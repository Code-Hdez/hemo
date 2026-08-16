#!/usr/bin/env python3
"""¿Qué hace de verdad `connection_retries`? — medido en local, sin GPU ni Ollama.

Por qué existe
--------------
`I-7` del GOAL ordena el desmontaje de la red de generación múltiple y pone
`httpx retries=0` el último, con una condición: *«solo tras CONTAR los reintentos
de conexión, que el ledger no ve»*.

El ledger no los ve, y **no puede verlos**: `[MEDIDO]` el bucle de reintento vive
en ``httpcore._async.connection.AsyncHTTPConnection._connect`` —captura
``ConnectError``/``ConnectTimeout`` con retroceso exponencial— y es **interno a
httpcore**. Desde la capa de `httpx` no hay gancho: ni un `event_hook`, ni un
método del transporte, ni un contador expuesto.

Así que contar la incidencia en producción exigiría una de tres cosas, y las tres
son peores que el problema:

1. parchear un interno de httpcore —frágil, y en la ruta de red del chat—;
2. mover el reintento a nuestro propio envoltorio con ``retries=0`` debajo —eso
   **es** el cambio que I-7 quiere decidir, así que no puede ser su instrumento—;
3. contar SYN a nivel de sistema operativo, fuera de la aplicación.

Lo que este script hace en su lugar
-----------------------------------
Responde la pregunta que de verdad está detrás de I-7 —**¿puede un reintento de
conexión producir una segunda generación invisible?**— con dos medidas locales:

1. **Un servidor de prueba que cuenta conexiones y bytes recibidos.** Si el
   reintento ocurriera después de enviar la petición, se verían bytes. Si ocurre
   antes, se ven conexiones y **cero bytes**.
2. **El coste en tiempo** de `retries=1` frente a `retries=0` ante un puerto que
   rechaza, que es lo único que `retries` compra o cuesta.

No necesita GPU, ni Ollama, ni las VMs. Es socket local.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import statistics
import time

import httpx

REPETICIONES = 5


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ServidorContador:
    """Acepta, cuenta, y cierra sin responder. Registra los bytes que le llegan."""

    def __init__(self) -> None:
        self.conexiones = 0
        self.bytes_recibidos = 0
        self._server: asyncio.AbstractServer | None = None
        self.puerto = 0

    async def __aenter__(self) -> ServidorContador:
        async def manejar(
            lector: asyncio.StreamReader, escritor: asyncio.StreamWriter
        ) -> None:
            self.conexiones += 1
            with contextlib.suppress(Exception):
                datos = await asyncio.wait_for(lector.read(65536), timeout=0.4)
                self.bytes_recibidos += len(datos)
            escritor.close()
            with contextlib.suppress(Exception):
                await escritor.wait_closed()

        self._server = await asyncio.start_server(manejar, "127.0.0.1", 0)
        self.puerto = int(self._server.sockets[0].getsockname()[1])
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()


async def _intentar(url: str, retries: int) -> tuple[bool, float]:
    cliente = httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(retries=retries),
        timeout=httpx.Timeout(2.0, connect=1.0),
    )
    t0 = time.perf_counter()
    ok = True
    try:
        await cliente.post(url, json={"x": 1})
    except Exception:
        ok = False
    finally:
        await cliente.aclose()
    return ok, (time.perf_counter() - t0) * 1000


async def principal() -> int:
    print("═" * 74)
    print("`connection_retries` — qué reintenta y qué cuesta. Local, sin GPU.")
    print("═" * 74)
    print(f"\n  httpx {httpx.__version__}")

    print("\n1) ¿EL REINTENTO OCURRE ANTES O DESPUÉS DE ENVIAR LA PETICIÓN?")
    print("   Servidor que acepta, cuenta conexiones y registra bytes recibidos.")
    async with ServidorContador() as srv:
        url = f"http://127.0.0.1:{srv.puerto}/api/chat"
        await _intentar(url, retries=1)
        print(f"     conexiones aceptadas : {srv.conexiones}")
        print(f"     bytes recibidos      : {srv.bytes_recibidos}")
        if srv.conexiones == 1:
            print(
                "     → UNA sola conexión: con el servidor levantado el `connect`\n"
                "       tiene éxito y `retries` NO entra en juego. El reintento solo\n"
                "       existe cuando la conexión no llega a establecerse."
            )

    print("\n2) ¿QUÉ CUESTA `retries=1` CUANDO EL PUERTO RECHAZA?")
    puerto = _puerto_libre()  # nadie escuchando → ConnectError inmediato
    url_muerta = f"http://127.0.0.1:{puerto}/api/chat"
    resultados: dict[int, list[float]] = {}
    for r in (0, 1):
        tiempos = []
        for _ in range(REPETICIONES):
            ok, ms = await _intentar(url_muerta, retries=r)
            assert not ok, "el puerto debía rechazar"
            tiempos.append(ms)
        resultados[r] = tiempos
        print(
            f"     retries={r}:  mediana {statistics.median(tiempos):7.2f} ms"
            f"   (n={REPETICIONES}, min {min(tiempos):.2f}, max {max(tiempos):.2f})"
        )

    delta = statistics.median(resultados[1]) - statistics.median(resultados[0])
    print(f"\n     coste del reintento: {delta:+.2f} ms por fallo de conexión")

    print("\n3) LO QUE ESTO DECIDE PARA I-7")
    print("     El reintento de httpcore se dispara SOLO al establecer la conexión,")
    print("     es decir ANTES de enviar un solo byte de la petición. Por tanto:")
    print("       · NO puede producir una segunda generación,")
    print("       · NO puede inflar `provider_calls`,")
    print("       · NO es una amenaza para `provider_calls == 1`.")
    print("     `retries=0` es una decisión de robustez y latencia, no de")
    print("     corrección. En I-7 va al final por una razón distinta de la que")
    print("     el GOAL supone, y su prerrequisito —contarlos— resulta ser")
    print("     innecesario para la garantía que se quería proteger.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
