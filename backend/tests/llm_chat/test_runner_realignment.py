"""El warmup pide el contexto correcto, pero sólo una vez en la vida del proceso.

`OllamaNativeLLMClient.warmup` envía el `num_ctx` del perfil —16384 en
producción— y lo hace bien. El problema es *cuándo*: se ejecuta al construir el
contenedor y no vuelve a ejecutarse nunca.

La VM de la GPU carga el mismo modelo con **su** contexto al validar el arranque
(`deploy/gpu/validate-runtime.sh`, que declara 65536). Cuando esa VM se reinicia,
el backend sigue vivo, no rehace el warmup, y el runner queda cargado con un
contexto que producción no pide. **El primer turno real paga la recarga.**

Medido contra la L4 de producción el 8-ago-2026:

    recarga por discordancia .... 96,3 · 100,8 · 101,0 · 101,3 · 101,7 s
                                   mediana 101,0 s   n=5
    llamada concordante ......... 0,55 s              -> 184x mas barato

    size_vram a num_ctx 16384 ... 16 926 501 764 B  (15,76 GiB)
    size_vram a num_ctx 65536 ... 18 889 436 036 B  (17,59 GiB)
                                   separacion 1,83 GiB = 11,6 %

`/api/ps` **no publica** el `num_ctx` con el que se cargó el runner, así que el
contexto no se puede comparar directamente. `size_vram` sí se publica, y la caché
KV escala con el contexto: es el único discriminador disponible desde fuera.

El disparador es un poll en segundo plano y no un gancho de post-generación a
propósito: comprobarlo después de generar arreglaría el turno 2 y dejaría al
primer usuario pagando los 101 s, que es exactamente lo que esto evita.

Los tests son síncronos y llaman a `asyncio.run`, como los otros veintidós
ficheros de esta suite. La primera versión usaba `@pytest.mark.asyncio`, que
pasaba en local y fallaba en CI con «async def functions are not natively
supported»: `pytest-asyncio` no está en `requirements-dev.txt` y sólo existía en
el entorno donde se escribió. Un verde local no es evidencia de un verde en CI
cuando el instrumento que lo produce no es el mismo.
"""

from __future__ import annotations

import asyncio
import json

import httpx

from app.modules.llm_chat.domain.generation_config import EffectiveGenerationProfile
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    OllamaNativeLLMClient,
)

# Los dos valores medidos contra produccion.
VRAM_16K = 16_926_501_764
VRAM_65K = 18_889_436_036


def _perfil() -> EffectiveGenerationProfile:
    return EffectiveGenerationProfile(
        name="warmup",
        kind="main",
        provider="ollama",
        model="qwen3.6:27b-q4_K_M",
        num_ctx=16384,
        max_input_tokens=12000,
        context_reserve_tokens=256,
        num_predict=1280,
        temperature=0.3,
        top_p=0.8,
        top_k=20,
        repeat_penalty=1.0,
        thinking=False,
        timeout_seconds=120.0,
        keep_alive=-1,
    )


class _Ollama:
    """Ollama de mentira que recuerda con qué `num_ctx` se le cargó."""

    def __init__(self, vram_inicial: int | None) -> None:
        self.vram = vram_inicial
        self.warmups: list[int] = []

    async def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            modelos = (
                []
                if self.vram is None
                else [{"name": "qwen3.6:27b-q4_K_M", "size_vram": self.vram}]
            )
            return httpx.Response(200, json={"models": modelos})
        if request.url.path == "/api/generate":
            cuerpo = json.loads(request.content)
            ctx = int(cuerpo["options"]["num_ctx"])
            self.warmups.append(ctx)
            # Cargar con el contexto del perfil deja la VRAM del perfil.
            self.vram = VRAM_16K if ctx == 16384 else VRAM_65K
            return httpx.Response(200, json={"response": "", "done": True})
        raise AssertionError(f"ruta inesperada: {request.url.path}")


def _cliente(ollama: _Ollama) -> OllamaNativeLLMClient:
    return OllamaNativeLLMClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(ollama.handler)),
        base_url="http://ollama:11434",
        model_name="qwen3.6:27b-q4_K_M",
        timeout_seconds=30.0,
        warmup_profile=_perfil(),
    )


def test_la_linea_base_la_fija_el_poll_no_el_warmup() -> None:
    async def _cuerpo() -> None:
        """La referencia la produce la primera observación del poll, no una constante."""
        ollama = _Ollama(vram_inicial=None)
        cliente = _cliente(ollama)

        assert await cliente.warmup(timeout_seconds=30.0) is True
        assert ollama.warmups == [16384]

        # El warmup no lee /api/ps: la referencia la fija la primera pasada del poll,
        # que es quien tiene ese trabajo.
        assert cliente._warmed_vram is None
        assert await cliente.capture_runner_baseline() == VRAM_16K


    asyncio.run(_cuerpo())


def test_no_rearma_cuando_el_runner_es_el_del_perfil() -> None:
    async def _cuerpo() -> None:
        """Sin discordancia no se toca nada: el poll tiene que ser barato."""
        ollama = _Ollama(vram_inicial=VRAM_16K)
        cliente = _cliente(ollama)
        await cliente.warmup(timeout_seconds=30.0)
        await cliente.capture_runner_baseline()
        ollama.warmups.clear()

        assert await cliente.realign_runner_if_drifted() is False
        assert ollama.warmups == []


    asyncio.run(_cuerpo())


def test_rearma_cuando_la_vm_dejo_el_runner_en_otro_contexto() -> None:
    async def _cuerpo() -> None:
        """El caso real: la VM de la GPU reinicia y carga a 65536.

        Sin esto, el desajuste sobrevive hasta que un usuario lo paga.
        """
        ollama = _Ollama(vram_inicial=VRAM_16K)
        cliente = _cliente(ollama)
        await cliente.warmup(timeout_seconds=30.0)
        await cliente.capture_runner_baseline()
        ollama.warmups.clear()

        ollama.vram = VRAM_65K  # la VM recargo con su contexto

        assert await cliente.realign_runner_if_drifted() is True
        assert ollama.warmups == [16384], "debe rearmar con el num_ctx del perfil"
        assert ollama.vram == VRAM_16K, "el runner queda alineado con produccion"


    asyncio.run(_cuerpo())


def test_rearma_cuando_no_hay_runner_residente() -> None:
    async def _cuerpo() -> None:
        """Sin modelo cargado el primer turno pagaria la carga entera."""
        ollama = _Ollama(vram_inicial=VRAM_16K)
        cliente = _cliente(ollama)
        await cliente.warmup(timeout_seconds=30.0)
        await cliente.capture_runner_baseline()
        ollama.warmups.clear()

        ollama.vram = None

        assert await cliente.realign_runner_if_drifted() is True
        assert ollama.warmups == [16384]


    asyncio.run(_cuerpo())


def test_una_diferencia_pequena_no_dispara_el_rearmado() -> None:
    async def _cuerpo() -> None:
        """La tolerancia existe porque `size_vram` es un proxy, no el `num_ctx`.

        La separación medida entre 16384 y 65536 es del 11,6 %; el umbral está al
        5 %, con holgura por ambos lados. Una variación menor —otra build del runner,
        otro redondeo— no debe costar una recarga de 101 s.
        """
        ollama = _Ollama(vram_inicial=VRAM_16K)
        cliente = _cliente(ollama)
        await cliente.warmup(timeout_seconds=30.0)
        await cliente.capture_runner_baseline()
        ollama.warmups.clear()

        ollama.vram = int(VRAM_16K * 1.02)

        assert await cliente.realign_runner_if_drifted() is False
        assert ollama.warmups == []


    asyncio.run(_cuerpo())


def test_un_ollama_que_no_responde_no_tumba_el_poll() -> None:
    async def _cuerpo() -> None:
        """Es mantenimiento en segundo plano: fallar aquí sólo repite el estado de hoy."""

        async def caido(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sin proveedor")

        cliente = OllamaNativeLLMClient(
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(caido)),
            base_url="http://ollama:11434",
            model_name="qwen3.6:27b-q4_K_M",
            timeout_seconds=1.0,
            warmup_profile=_perfil(),
        )

        assert await cliente.resident_runner_vram() is None
        assert await cliente.realign_runner_if_drifted() is False


    asyncio.run(_cuerpo())


def test_sin_referencia_buena_no_se_adopta_la_lectura_actual() -> None:
    async def _cuerpo() -> None:
        """La trampa que tuvo la primera versión de este código.

        Si el poll mira por primera vez cuando la deriva YA ocurrió, adoptar esa
        lectura como referencia congela el estado malo y no se rearma nunca. Sin
        referencia de un estado bueno, la respuesta correcta es no decidir.
        """
        ollama = _Ollama(vram_inicial=VRAM_65K)
        cliente = _cliente(ollama)  # sin warmup: no hay referencia

        assert await cliente.realign_runner_if_drifted() is False
        assert cliente._warmed_vram is None, "no debe adoptar el estado derivado"
        assert ollama.warmups == []


    asyncio.run(_cuerpo())
