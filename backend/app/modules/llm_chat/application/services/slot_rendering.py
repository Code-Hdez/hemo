"""Que escriba el servidor: slots restringidos y prosa ensamblada.

Qué resuelve
------------
`ambiguous_parameter_claim` fue **31 de los 96** fallos de contrato de la campaña
v3, y los 31 son neutrófilos. La comprobación salta cuando una cláusula nombra la
**familia genérica** del parámetro y el paciente tiene el absoluto y el porcentaje
**con estados distintos**. Detecta una ambigüedad **real**: en 2429 hemogramas
reales del proyecto divergen en el 43,5 % (NEU), 35,8 % (LYM) y 29,8 % (MONO).

Cuatro intentos de instruir al modelo fracasaron, medidos y revertidos: `SEL-01`
dispara la clase **9 de 9** aun con la instrucción activa. La vía que queda no es
instruir mejor: es **no darle la ocasión**. El modelo emite slots; el servidor
escribe la frase.

El hallazgo que fija el formato, y que costó ejecutarlo
------------------------------------------------------
El plan proponía desambiguar por el nombre —«el recuento absoluto de
neutrófilos»—. **No funciona**, y se comprobó ejecutando el validador en vez de
leerlo:

    «Los neutrófilos están altos»                                      inválido
    «El recuento absoluto de neutrófilos es de 8.4 x10^3/uL, dentro
     del rango»                                                        inválido  ← la propuesta
    «Neutrófilos, recuento absoluto.
     Valor medido: 8.4 x10^3/uL, dentro del rango»                     VÁLIDO

`generic_family_mentions` marca `generic_family=True` para **cualquier** alias del
absoluto: `neutrofilos`, `NEU`, `NEU#`. Solo el porcentaje se desambigua solo,
porque su alias lleva `%`/`pct`/`porcentaje` dentro. Lo que sí funciona es
**separar la etiqueta del valor en cláusulas distintas**: la cláusula que nombra
el parámetro no lleva cifra ni estado, y la que los lleva no nombra el parámetro.

Nada de esto toca el validador ni cambia qué está autorizado. El porcentaje sigue
siendo un hecho citable; lo que cambia es que el modelo ya no escribe la frase
ambigua en la posición donde el validador mira.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = [
    "AfirmacionSlot",
    "ProsaSaneada",
    "construir_esquema_de_turno",
    "etiqueta_desambiguada",
    "renderizar_afirmaciones",
    "sanear_prosa",
]

# Estados que el SERVIDOR calcula. El modelo elige entre ellos, no los infiere.
_TEXTO_ESTADO = {
    "low": "por debajo del rango de referencia",
    "bajo": "por debajo del rango de referencia",
    "normal": "dentro del rango de referencia",
    "dentro_del_rango": "dentro del rango de referencia",
    "high": "por encima del rango de referencia",
    "alto": "por encima del rango de referencia",
}
ESTADOS_SLOT = ("bajo", "dentro_del_rango", "alto")
_CANONICO = {
    "low": "bajo",
    "bajo": "bajo",
    "normal": "dentro_del_rango",
    "dentro_del_rango": "dentro_del_rango",
    "high": "alto",
    "alto": "alto",
}

# Un valor citable: número en cadena. Nunca `minimum`/`maximum` — los rangos
# numéricos no se enforcan para no-enteros, y estas cifras son decimales.
_NUMERO = re.compile(r"^-?\d+(?:[.,]\d+)?$")


@dataclass(frozen=True)
class AfirmacionSlot:
    """Lo que el modelo emite. Nada de esto es prosa."""

    parametro: str
    estado: str
    valor: str | None = None
    fecha: str | None = None


def _es_porcentaje(codigo: str) -> bool:
    return codigo.strip().upper().endswith(("_PCT", "_PORCENTAJE"))


def etiqueta_desambiguada(codigo: str, nombre: str | None = None) -> str:
    """La etiqueta va SOLA en su cláusula: sin cifra y sin estado.

    Para el porcentaje se antepone «Porcentaje de», que además hace que
    `_is_explicit_percent` lo reconozca. Para el absoluto no existe ninguna forma
    que evite `generic_family`, así que la desambiguación la da la **posición**,
    no la palabra: por eso esta cadena nunca se concatena con el valor.
    """
    limpio = (nombre or codigo).strip()
    if _es_porcentaje(codigo):
        base = re.sub(r"\s*%\s*$|\s+pct$", "", limpio, flags=re.IGNORECASE).strip()
        return f"Porcentaje de {base.lower()}"
    return f"{limpio}, recuento absoluto"


def _valores_citables(hechos: list[dict[str, Any]], codigo: str) -> list[str]:
    salida: list[str] = []
    for h in hechos:
        if str(h.get("code") or "").strip().upper() != codigo:
            continue
        crudo = str(h.get("value") or "").strip().replace(",", ".")
        if _NUMERO.match(crudo) and crudo not in salida:
            salida.append(crudo)
    return salida


def construir_esquema_de_turno(hechos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """El esquema del turno. Los `enum` se construyen POR TURNO, no una vez.

    Contienen solo los códigos y valores que el selector puso en el contexto de
    **este** turno. Es la versión mecánica del gradiente medido —0 % de fallo con
    1 hecho, 5,7 % con 2, 11,5 % con 4—: menos candidatos, menos confusión. Y el
    selector nunca deja fuera un parámetro pedido (0 de 405), así que no cuesta
    cobertura.
    """
    codigos: list[str] = []
    valores: list[str] = []
    fechas: list[str] = []
    for h in hechos:
        c = str(h.get("code") or "").strip().upper()
        if c and c not in codigos:
            codigos.append(c)
        v = str(h.get("value") or "").strip().replace(",", ".")
        if _NUMERO.match(v) and v not in valores:
            valores.append(v)
        f = str(h.get("study_date") or "").strip()
        if f and f not in fechas:
            fechas.append(f)
    if not codigos:
        return None

    propiedades: dict[str, Any] = {
        "parametro": {"enum": sorted(codigos)},
        "estado": {"enum": list(ESTADOS_SLOT)},
    }
    if valores:
        # `enum` de literales en CADENA, nunca `number` con `minimum`/`maximum`.
        propiedades["valor"] = {"enum": sorted(valores)}
    if fechas:
        # La fecha va en el enum a propósito: aporta dígitos que el validador
        # numérico acepta como respaldo, así que conviene que el respaldo sea real.
        propiedades["fecha"] = {"enum": sorted(fechas)}

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["afirmaciones", "explicacion"],
        "properties": {
            "afirmaciones": {
                "type": "array",
                "minItems": 0,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["parametro", "estado"],
                    "properties": propiedades,
                },
            },
            "explicacion": {"type": "string"},
        },
    }


def renderizar_afirmaciones(
    afirmaciones: list[AfirmacionSlot],
    hechos: list[dict[str, Any]],
) -> str:
    """Ensambla la prosa. La etiqueta y el valor van en cláusulas SEPARADAS.

    Ese punto entre las dos es el mecanismo entero, y está verificado contra el
    validador real: pegarlas en una sola cláusula vuelve a disparar
    `ambiguous_parameter_claim`.
    """
    por_codigo = {str(h.get("code") or "").strip().upper(): h for h in hechos}
    lineas: list[str] = []
    for a in afirmaciones:
        codigo = a.parametro.strip().upper()
        hecho = por_codigo.get(codigo)
        if hecho is None:
            continue  # el enum lo impide; si pasa, se omite en vez de inventar
        etiqueta = etiqueta_desambiguada(codigo, str(hecho.get("parameter") or ""))
        estado = _TEXTO_ESTADO.get(_CANONICO.get(a.estado, a.estado), "")
        unidad = str(hecho.get("unit") or "").strip()
        valor = (a.valor or str(hecho.get("value") or "")).strip()

        # Cláusula 1: solo la etiqueta. Ni cifra ni estado.
        lineas.append(f"{etiqueta}.")
        # Cláusula 2: valor y estado, sin nombrar el parámetro.
        partes = []
        if valor:
            partes.append(f"Valor medido: {valor}" + (f" {unidad}" if unidad else ""))
        if estado:
            partes.append(estado)
        if partes:
            lineas.append(", ".join(partes) + ".")
    return "\n".join(lineas)


# ── El saneado de la prosa libre ────────────────────────────────────────────
# Anexo A §5: *el servidor pasa su propio borrador por los predicados existentes
# antes de ensamblar*. Eso **no es tocar el validador** (`I-2`): es aplicarlo, sin
# cambiarlo, a un texto que todavía no se ha publicado.
#
# Anexo A §6: **si la prosa incumple, se recorta — no se reintenta.** Reintentar
# multiplicaría `provider_calls` y chocaría de frente con la Fase 4. El coste de
# recortar se mide como sobre-rechazo, no se esconde.

_SEPARADOR_ORACION = re.compile(r"(?<=[.!?;:\n])\s+")
_FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_UNIDAD_CIENTIFICA = re.compile(r"[x×]\s*10\s*[\^³⁹]?\s*\d*\s*/?\s*[µu]?[lL]?", re.IGNORECASE)
_CIFRA_LIBRE = re.compile(r"(?<![\d.,-])(\d{1,3}(?:[.,]\d{1,2})?)(?![\d,]|\.\d)")
# Una enumeración («1.», «2)») no es una cifra del paciente.
_ORDINAL = re.compile(r"^\s*\**\s*\d{1,2}[.)]\s")
# Y un fragmento que es SOLO el marcador tampoco: lo produce el propio
# separador de oraciones al partir «1. Los glóbulos…».
_SOLO_MARCADOR = re.compile(r"[\s*\-–—]*\d{1,2}\s*[.)\-:]?[\s*]*")


@dataclass(frozen=True)
class ProsaSaneada:
    texto: str
    oraciones_quitadas: int
    motivos: tuple[str, ...]

    @property
    def hubo_recorte(self) -> bool:
        return self.oraciones_quitadas > 0


def _lleva_cifra_de_paciente(oracion: str) -> bool:
    if _ORDINAL.match(oracion):
        return False
    # El separador de oraciones parte «1. Los glóbulos…» en dos, así que el
    # marcador de lista llega solo. Contarlo como oración recortada INFLARÍA el
    # sobre-rechazo de M.5, que es justo la métrica que decide si esto vale.
    # Lo encontró un test, no la lectura.
    if _SOLO_MARCADOR.fullmatch(oracion.strip()):
        return False
    limpia = _UNIDAD_CIENTIFICA.sub(" ", _FECHA.sub(" ", oracion))
    return bool(_CIFRA_LIBRE.search(limpia))


def sanear_prosa(
    texto: str,
    *,
    predicados: dict[str, Any] | None = None,
) -> ProsaSaneada:
    """Quita de la prosa libre lo que el servidor va a escribir por su cuenta.

    Se recorta una oración cuando lleva **una cifra del paciente**, **una
    afirmación de estado**, o **casa un predicado de seguridad**. Las tres cosas
    las escribe el servidor —o no deben escribirse en absoluto—, así que dejarlas
    en la prosa solo abre la ocasión de que el validador las rechace.

    `predicados` se inyecta para poder probar esto sin arrastrar el validador
    entero; por defecto usa los de producción, sin modificarlos.
    """
    if not texto.strip():
        return ProsaSaneada(texto="", oraciones_quitadas=0, motivos=())

    if predicados is None:
        from .output_claim_validator import OutputClaimValidator  # noqa: PLC0415
        from .output_validator import OutputValidator  # noqa: PLC0415

        ov = OutputValidator()
        predicados = {
            "estado": lambda s: bool(OutputClaimValidator._status_claims(s)),  # noqa: SLF001
            "indirect_treatment": lambda s: bool(ov._contains_indirect_treatment(s)),  # noqa: SLF001
            "definitive_diagnosis": lambda s: ov._contains_definitive_diagnosis(s),  # noqa: SLF001
            "dose_instruction": lambda s: bool(  # noqa: SLF001
                ov._contains_positive_dose_instruction(s)
            ),
        }

    conservadas: list[str] = []
    motivos: list[str] = []
    for oracion in _SEPARADOR_ORACION.split(texto):
        if not oracion.strip():
            continue
        motivo: str | None = None
        if _lleva_cifra_de_paciente(oracion):
            motivo = "cifra"
        else:
            for nombre, fn in predicados.items():
                if fn(oracion):
                    motivo = nombre
                    break
        if motivo is None:
            conservadas.append(oracion.strip())
        else:
            motivos.append(motivo)

    return ProsaSaneada(
        texto=" ".join(conservadas).strip(),
        oraciones_quitadas=len(motivos),
        motivos=tuple(motivos),
    )
