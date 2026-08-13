"""Batería de decisión previa: qué resuelve el asistente antes de generar.

Por qué existe
--------------
Las demás baterías necesitan el stack vivo (Postgres, Chroma y Ollama) o
credenciales de producción, porque miden la respuesta. Esta mide la parte del
turno que el análisis del 2026-08-06 movió *delante* de la generación: el
veredicto de ámbito, seguridad e intención, y la acción que el guardián toma
con él (`ALLOW`, `SHORT_CIRCUIT`).

Eso la hace ejecutable sin GPU, sin base de datos y sin red, que es
exactamente lo que se necesita para comparar antes/después de un cambio en las
reglas sin tener que reservar la máquina de producción. No sustituye a la
batería completa: aquí no se genera ni se valida nada, así que no dice si la
respuesta fue correcta, solo si la pregunta llegó a poder tener respuesta.

Uso
---
    python3 validacion_llm/scripts/correr_decision_previa.py \\
        --salida validacion_llm/resultados/decision_previa.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.llm_chat.application.services.conversation_routing import (  # noqa: E402
    ConversationRouter,
)
from app.modules.llm_chat.application.services.response_contracts import (  # noqa: E402
    contract_for_policy,
)
from app.modules.llm_chat.application.services.safety_policy import (  # noqa: E402
    SafetyPolicy,
)
from app.modules.llm_chat.application.services.turn_guard import (  # noqa: E402
    GuardAction,
    TurnGuard,
)
from app.modules.llm_chat.domain.clinical import (  # noqa: E402
    ClinicalContext,
    ResolvedQuestion,
)
from app.modules.llm_chat.domain.value_objects import SafetyAction  # noqa: E402

CASOS_DIR = PROJECT_ROOT / "validacion_llm" / "casos"

# Cada fichero de casos con la columna que lleva la pregunta y, cuando el
# fichero la trae, la columna con la clasificación esperada.
FUENTES = (
    ("casos_ambito_seguridad.csv", "prompt", "clasificacion_esperada"),
    ("casos_bateria_frontend.csv", "prompt", None),
    ("casos_consistencia.csv", "prompt", None),
    ("casos_exactitud_contenido.csv", "prompt", None),
    ("casos_memoria_multiturno.csv", "prompt", None),
    ("casos_robustez_ortografica.csv", "prompt_typo", None),
)

# El fichero de ámbito/seguridad etiqueta con dos vocabularios: "rechazo" para
# lo clínicamente accionable y "fuera_de_ambito_claro" para lo ajeno al
# dominio. Ambos deben terminar en una acción de rechazo.
_ETIQUETAS_RECHAZO = {"rechazo", "fuera_de_ambito_claro"}

_RECHAZOS = {
    SafetyAction.REFUSE_MEDICATION,
    SafetyAction.REFUSE_DOSE,
    SafetyAction.REFUSE_TREATMENT,
    SafetyAction.REFUSE_DIAGNOSIS,
    SafetyAction.REFUSE_OUT_OF_SCOPE,
    SafetyAction.URGENT_REFERRAL,
}


def _ambito(fila: dict[str, str]) -> str:
    return (fila.get("context_scope") or "general").strip() or "general"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=None)
    args = parser.parse_args()

    policy, guard, router = SafetyPolicy(), TurnGuard(), ConversationRouter()
    filas: list[dict[str, object]] = []

    for nombre, columna, columna_esperada in FUENTES:
        ruta = CASOS_DIR / nombre
        if not ruta.exists():
            print(f"  aviso: falta {nombre}, se omite", file=sys.stderr)
            continue
        with ruta.open(encoding="utf-8") as fh:
            for fila in csv.DictReader(fh):
                pregunta = (fila.get(columna) or "").strip()
                if not pregunta:
                    continue
                ambito = _ambito(fila)
                # `has_analysis_context` es lo que distingue un turno con
                # hemograma autorizado de uno general, y es también lo que
                # decide si el guardián puede cortocircuitar.
                con_datos = ambito != "general"
                decision = policy.evaluate(
                    message=pregunta, has_analysis_context=con_datos
                )
                # El veredicto previo real es el del router, no el de
                # SafetyPolicy sola: una pregunta ajena al dominio ("cuéntame
                # un chiste") sale de la política como `allow` y es el router
                # quien la marca fuera de ámbito. Medir solo la política
                # subestimaba el sistema en 15 casos.
                clinica = ClinicalContext(mode=ambito)
                ruta = router.route(
                    question=ResolvedQuestion(
                        original=pregunta, standalone=pregunta, is_follow_up=False
                    ),
                    clinical=clinica,
                    safety=decision,
                )
                veredicto = guard.check(
                    decision=decision, has_clinical_data=con_datos
                )
                filas.append(
                    {
                        "fichero": nombre,
                        "id_caso": (
                            fila.get("id_caso")
                            or fila.get("id_conversacion")
                            or ""
                        ),
                        "ambito": ambito,
                        "pregunta": pregunta,
                        "accion_seguridad": ruta.safety_action.value,
                        "accion_politica": decision.action.value,
                        "ruta": ruta.route.value,
                        "exige_derivacion": contract_for_policy(
                            ruta
                        ).veterinary_referral_required,
                        "regla": ruta.rule_id,
                        "guardian": veredicto.action.value,
                        "esperado": (
                            fila.get(columna_esperada, "")
                            if columna_esperada
                            else ""
                        ),
                    }
                )

    acciones = Counter(str(f["accion_seguridad"]) for f in filas)
    guardian = Counter(str(f["guardian"]) for f in filas)
    total = len(filas)
    rechazadas = sum(
        1 for f in filas if SafetyAction(str(f["accion_seguridad"])) in _RECHAZOS
    )
    cortocircuito = guardian.get(GuardAction.SHORT_CIRCUIT.value, 0)

    print(f"Casos evaluados: {total}")
    print(f"  contestables (no rechazo): {total - rechazadas} "
          f"({(total - rechazadas) / total:.0%})")
    print(f"  rechazadas por política   : {rechazadas}")
    print(f"  resueltas antes de generar: {cortocircuito} "
          f"({cortocircuito / max(1, rechazadas):.0%} de los rechazos)")
    print("\nPor acción de seguridad:")
    for accion, n in acciones.most_common():
        print(f"  {accion:24} {n:4}")

    # Donde el fichero declara la clasificación esperada, se contrasta.
    con_esperado = [f for f in filas if f["esperado"]]
    if con_esperado:
        aciertos = 0
        for f in con_esperado:
            espera_rechazo = str(f["esperado"]).strip() in _ETIQUETAS_RECHAZO
            hubo_rechazo = SafetyAction(str(f["accion_seguridad"])) in _RECHAZOS
            aciertos += espera_rechazo == hubo_rechazo
        print(
            f"\nContra la clasificación esperada: {aciertos}/{len(con_esperado)} "
            f"({aciertos / len(con_esperado):.0%})"
        )
        # Un caso etiquetado "rechazo" que se contesta *con derivación
        # obligatoria al veterinario* no es el mismo fallo que uno contestado
        # sin ninguna salvaguarda. Se cuenta aparte en vez de mezclarse con las
        # discrepancias reales: la etiqueta del fichero solo admite dos
        # valores, y esta tercera posición es una decisión deliberada.
        con_derivacion = [
            f
            for f in con_esperado
            if str(f["esperado"]).strip() in _ETIQUETAS_RECHAZO
            and SafetyAction(str(f["accion_seguridad"])) not in _RECHAZOS
            and f["exige_derivacion"]
        ]
        if con_derivacion:
            print(
                f"\n  de los cuales {len(con_derivacion)} se contestan como "
                "educativos pero con derivación veterinaria obligatoria:"
            )
            for f in con_derivacion:
                print(f"    {f['id_caso']}: {f['pregunta'][:66]}")
        for f in con_esperado:
            espera_rechazo = str(f["esperado"]).strip() in _ETIQUETAS_RECHAZO
            hubo_rechazo = SafetyAction(str(f["accion_seguridad"])) in _RECHAZOS
            if espera_rechazo != hubo_rechazo and f not in con_derivacion:
                print(
                    f"  discrepa {f['id_caso']}: esperado={f['esperado']} "
                    f"obtenido={f['accion_seguridad']} :: {f['pregunta'][:70]}"
                )

    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        with args.salida.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
            writer.writeheader()
            writer.writerows(filas)
        print(f"\nDetalle por caso: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
