"""Atribución de fuentes derivada en el servidor, con etiqueta honesta.

Por qué existe
--------------
Hasta ahora el modelo declaraba `source_ids` y `evidence_spans` dentro del sobre,
y además emitía un marcador `[[EVIDENCE_USED:S1,S2]]` al final del texto. Las dos
cosas son autodeclaración: el modelo puede citar una fuente que no leyó, u
omitir la que sí usó. De las 10 reparaciones de la batería del 10-ago, **2
fueron `missing_evidence_attribution`** — el modelo no rellenó una atribución que
el servidor ya podía calcular.

El servidor sabe exactamente qué fuentes retuvo y metió en el prompt. Eso es un
hecho, no una inferencia.

La distinción que este módulo protege
-------------------------------------
**«Fuentes consultadas» ≠ «prueba de esta afirmación».** Son cosas distintas y
confundirlas es una de las señales de desvío declaradas del proyecto: *«dar las
fuentes recuperadas como prueba de cada afirmación»*.

- `consultadas` es un **hecho del servidor**: lo que se puso en el prompt.
- `solapamiento` es una **medida léxica**, no una demostración de que la fuente
  sustente la frase. Se entrega con su nombre y su valor para que quien la
  consuma decida, y **nunca** se presenta como evidencia.

La prueba por proposición —entailment real— es trabajo aparte, con el
verificador ONNX que ya está en el repositorio, y solo debe activarse cuando se
exija de verdad. Este módulo no la finge.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Palabras demasiado comunes para que su presencia diga nada sobre el uso de una
# fuente. Sin este filtro, cualquier texto en español "solapa" con cualquier
# fuente en español.
_VACIAS = frozenset(
    """
    el la los las un una unos unas de del al a en y o u que se su sus por para
    con sin sobre entre como mas menos muy este esta estos estas ese esa eso
    aquel es son ser estar hay ha han he puede pueden debe deben si no lo le
    les nos me te ya cuando donde porque pero tambien solo cada todo toda todos
    todas otro otra otros otras mismo misma
    """.split()
)

_PALABRA = re.compile(r"[a-z0-9]{4,}")


def _plano(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .casefold()
    )


def _terminos(texto: str) -> set[str]:
    return {p for p in _PALABRA.findall(_plano(texto)) if p not in _VACIAS}


@dataclass(frozen=True, slots=True)
class SolapamientoFuente:
    """Cuánto del vocabulario distintivo de una fuente reaparece en el texto.

    **No es evidencia de que la fuente sustente la respuesta.** Es una medida
    léxica. El nombre del campo lo dice a propósito.
    """

    source_id: str
    chunk_id: str
    terminos_fuente: int
    terminos_compartidos: int

    @property
    def fraccion(self) -> float:
        if not self.terminos_fuente:
            return 0.0
        return self.terminos_compartidos / self.terminos_fuente


@dataclass(frozen=True, slots=True)
class AtribucionDeFuentes:
    """Lo que el servidor puede afirmar sobre las fuentes de un turno."""

    # HECHO: lo que el servidor puso en el prompt. Etiqueta honesta para el
    # público: «fuentes consultadas», jamás «fuentes que lo demuestran».
    consultadas: tuple[str, ...] = ()
    # MEDIDA léxica, ordenada de mayor a menor solapamiento. No es prueba.
    solapamiento: tuple[SolapamientoFuente, ...] = ()

    def por_encima_de(self, umbral: float) -> tuple[str, ...]:
        """Fuentes cuyo solapamiento supera un umbral.

        Sigue sin ser prueba: es un filtro sobre una medida léxica. Quien lo use
        para etiquetar debe seguir diciendo «consultadas».
        """
        return tuple(
            dict.fromkeys(
                s.source_id for s in self.solapamiento if s.fraccion >= umbral
            )
        )


def atribuir_fuentes(
    texto: str,
    fuentes: list[object] | None,
) -> AtribucionDeFuentes:
    """Deriva qué fuentes se consultaron y cuánto reaparecen en el texto.

    `fuentes` son los fragmentos que el servidor retuvo y metió en el prompt
    (`RetrievedChunk` o cualquier objeto con `source_id`, `id` y `text`).
    """
    if not fuentes:
        return AtribucionDeFuentes()

    consultadas: list[str] = []
    medidas: list[SolapamientoFuente] = []
    del_texto = _terminos(texto) if texto.strip() else set()

    for fuente in fuentes:
        source_id = str(getattr(fuente, "source_id", "") or "")
        if source_id and source_id not in consultadas:
            consultadas.append(source_id)
        propios = _terminos(str(getattr(fuente, "text", "") or ""))
        medidas.append(
            SolapamientoFuente(
                source_id=source_id,
                chunk_id=str(getattr(fuente, "id", "") or ""),
                terminos_fuente=len(propios),
                terminos_compartidos=len(propios & del_texto),
            )
        )

    medidas.sort(key=lambda s: (-s.fraccion, s.source_id))
    return AtribucionDeFuentes(
        consultadas=tuple(consultadas),
        solapamiento=tuple(medidas),
    )
