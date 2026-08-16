"""Atribución de hechos derivada del texto, en el servidor.

Por qué existe
--------------
Hasta ahora el modelo declaraba él mismo qué hechos del paciente sustentaban
cada afirmación, rellenando `fact_ids` dentro del sobre estructurado. Eso tiene
tres problemas y los tres están medidos:

1. **No es verificación, es autodeclaración.** El modelo puede escribir un
   `fact_id` correcto junto a una cifra equivocada, o al revés.
2. **Cuesta tokens.** En la Puerta 0, el 67,7 % de lo que el modelo escribe es
   sobre y no prosa: 194 de 321 tokens de mediana.
3. **Es la causa principal de reparación.** De las 10 reparaciones de la batería
   del 10-ago, 3 fueron `structured_patient_fact_id_required` — el modelo no
   declaró un identificador que el servidor ya conocía.

El servidor sabe exactamente qué hechos inyectó en el prompt. No necesita que se
los devuelvan: necesita comprobar si el texto los usó bien. Eso es determinista.

Qué hace y qué NO hace
----------------------
Empareja cada cifra del texto con los hechos autorizados por **valor**, y exige
además que el parámetro esté **nombrado cerca** para atribuirlo. Devuelve
también las cifras que no corresponden a ningún hecho autorizado, que es la
señal de alucinación numérica.

**No sustituye a `OutputValidator`.** Éste deriva atribución; aquél decide si la
respuesta es publicable. La seguridad clínica sigue donde estaba.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.modules.llm_chat.application.services.clinical_facts import (
    LabFact,
    temporal_fact_index,
)

# Ventana, en caracteres, dentro de la que un nombre de parámetro se considera
# "cerca" de una cifra. Un hemograma escrito en prosa española pone el nombre a
# menos de una oración de su valor; más allá de eso la cercanía deja de ser
# evidencia y pasa a ser coincidencia.
VENTANA_CERCANIA = 90

# Tolerancia relativa al comparar una cifra del texto con el valor autorizado.
# No es cero porque el modelo redondea al escribir en prosa ("unos 15,2").
TOLERANCIA_RELATIVA = 0.005

_NUMERO = re.compile(r"(?<![\w.,^])(\d{1,4}(?:[.,]\d{1,3})?)(?![\w])")

# Los exponentes de las unidades («x10^9/L», «10⁶/µL») son parte de la unidad, no
# cifras clínicas. Se neutralizan antes de escanear para que el «9» de x10^9 no
# se contabilice como una afirmación numérica sin respaldo.
_UNIDAD_EXPONENTE = re.compile(r"(?:x\s*)?10\s*(?:\^|\*\*|[\u2070-\u209f])\s*-?\d+")


def _plano(texto: str) -> str:
    """Minúsculas sin acentos, para comparar nombres de parámetro."""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .casefold()
    )


def _cifras(texto: str) -> list[tuple[float, int, int]]:
    """Las cifras del texto con su posición: (valor, inicio, fin).

    Las posiciones son las del texto ORIGINAL: los exponentes de unidad se
    sustituyen por espacios del mismo largo para no desplazar los índices.
    """
    limpio = _UNIDAD_EXPONENTE.sub(lambda m: " " * len(m.group(0)), texto)
    encontrados: list[tuple[float, int, int]] = []
    for m in _NUMERO.finditer(limpio):
        crudo = m.group(1).replace(",", ".")
        try:
            encontrados.append((float(crudo), m.start(1), m.end(1)))
        except ValueError:  # pragma: no cover - el patrón ya lo garantiza
            continue
    return encontrados


def _nombres(hecho: LabFact) -> tuple[re.Pattern[str], ...]:
    """Patrones con frontera de palabra.

    Buscar el nombre como subcadena da falsos positivos devastadores con
    códigos cortos: «A» casa dentro de «por ahí», y entonces una cifra ambigua
    se atribuye al hecho equivocado con toda confianza.
    """
    candidatos = (
        hecho.code,
        hecho.canonical_name,
        hecho.display_name,
        *hecho.aliases,
    )
    vistos = {_plano(n) for n in candidatos if n and n.strip()}
    return tuple(
        re.compile(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])") for n in vistos
    )


def _coincide(valor: float, referencia: float) -> bool:
    if referencia == 0:
        return abs(valor) < 1e-9
    return abs(valor - referencia) <= abs(referencia) * TOLERANCIA_RELATIVA


@dataclass(frozen=True, slots=True)
class CifraAtribuida:
    """Una cifra del texto y el hecho autorizado que la sostiene."""

    valor: float
    inicio: int
    fin: int
    fact_id: str
    code: str
    nombrado_cerca: bool


@dataclass(frozen=True, slots=True)
class AtribucionDeHechos:
    """Lo que el servidor deriva del texto, sin preguntarle al modelo."""

    fact_ids: tuple[str, ...] = ()
    atribuidas: tuple[CifraAtribuida, ...] = ()
    # Cifras del texto que no corresponden a NINGÚN hecho autorizado. Es la
    # señal de alucinación numérica, y se entrega cruda: decidir qué hacer con
    # ella es de OutputValidator, no de aquí.
    sin_respaldo: tuple[float, ...] = ()
    # Hechos que el servidor inyectó y el texto no llegó a usar. No es un error:
    # una respuesta puede citar dos parámetros de doce. Sirve para medir
    # cobertura sin exigirla.
    no_usados: tuple[str, ...] = field(default=())

    @property
    def hay_cifra_sin_respaldo(self) -> bool:
        return bool(self.sin_respaldo)


def atribuir_hechos(
    texto: str,
    case_facts: list[dict[str, object]] | None,
) -> AtribucionDeHechos:
    """Deriva del texto qué hechos autorizados sostiene, y cuáles no.

    Sustituye a los `fact_ids` que el modelo autodeclaraba. El servidor conoce
    los hechos que inyectó; aquí solo comprueba cuáles aparecen de verdad.
    """
    if not texto.strip() or not case_facts:
        return AtribucionDeHechos()

    indice = temporal_fact_index(list(case_facts))
    hechos = [h for lista in indice.by_code.values() for h in lista]
    if not hechos:
        return AtribucionDeHechos()

    plano = _plano(texto)
    atribuidas: list[CifraAtribuida] = []
    sin_respaldo: list[float] = []
    usados: set[str] = set()

    for valor, inicio, fin in _cifras(texto):
        candidatos = [
            h for h in hechos if h.value is not None and _coincide(valor, h.value)
        ]
        if not candidatos:
            # Antes de llamarla huérfana: ¿es un límite de rango autorizado?
            # Decir "el rango es 5,5 a 16,9" no inventa nada.
            if any(
                lim is not None and _coincide(valor, lim)
                for h in hechos
                for lim in (h.reference_low, h.reference_high)
            ):
                continue
            sin_respaldo.append(valor)
            continue

        ventana = plano[
            max(0, inicio - VENTANA_CERCANIA) : min(len(plano), fin + VENTANA_CERCANIA)
        ]
        nombrado = [
            h for h in candidatos if any(p.search(ventana) for p in _nombres(h))
        ]
        # Si el parámetro se nombra cerca, ése es el hecho. Si no, sólo se
        # atribuye cuando el valor identifica un único hecho sin ambigüedad.
        elegido: LabFact | None = None
        if len(nombrado) == 1:
            elegido = nombrado[0]
        elif not nombrado and len(candidatos) == 1:
            elegido = candidatos[0]
        if elegido is None:
            continue

        atribuidas.append(
            CifraAtribuida(
                valor=valor,
                inicio=inicio,
                fin=fin,
                fact_id=elegido.fact_id,
                code=elegido.code,
                nombrado_cerca=bool(nombrado),
            )
        )
        if elegido.fact_id:
            usados.add(elegido.fact_id)

    todos = {h.fact_id for h in hechos if h.fact_id}
    return AtribucionDeHechos(
        fact_ids=tuple(sorted(usados)),
        atribuidas=tuple(atribuidas),
        sin_respaldo=tuple(sin_respaldo),
        no_usados=tuple(sorted(todos - usados)),
    )
