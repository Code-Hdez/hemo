# 07 — Árbol de causa raíz (con segundos medidos)

Base: 4.940 s de latencia observada en 70 preguntas.

```
LATENCIA TOTAL 4.940 s (mediana 59,1 s/pregunta)
│
├── SUELO FÍSICO POR GENERACIÓN ......... 2.803 s (56,8 %)
│   ├── decode 1.ª generación ........... 2.365 s (47,9 %)  CONFIRMADO
│   │     mecanismo: 13,04-13,71 tok/s medidos directamente contra el modelo;
│   │     mediana 375 tok de salida -> ~29 s por respuesta
│   │     palancas: GPU con más ancho de banda | modelo menor | MTP
│   │     margen de engine: 8-14 % (upstream Ollama vs llama.cpp) NO_OBSERVABLE aquí
│   └── prefill 1.ª generación .......... 438 s (8,9 %)     CONFIRMADO
│         ya amortiguado: el caché ahorra 24,2 % de tokens de entrada
│
├── AMPLIFICACIÓN POR PIPELINE .......... 1.989 s (40,3 %)  ← EVITABLE
│   ├── decode 2.ª/3.ª/4.ª generación ... 1.876 s (38,0 %)  CONFIRMADO
│   └── prefill de regeneraciones ....... 113 s (2,3 %)
│   │
│   └── CAUSA EXACTA DE LAS REGENERACIONES
│       ├── CONTRATO: schema acepta / validador rechaza .... CONFIRMADO
│       │     GeneratedClaim.required = [claim_id, text, claim_type]
│       │     policy_rule_ids / fact_ids NO son required -> la gramática
│       │     permite [] ; la regla structured_response.py:140 lo prohíbe
│       │     para ciertos claim_type. JSON Schema no expresa esa condición.
│       │     -> policy_rule_id_missing (15), patient_fact_ids_missing (6)
│       ├── GROUNDING/COBERTURA ........................... CONFIRMADO
│       │     missing_required_clinical_facts (21):
│       │     PLT:value, PLT:unit, WBC:value... el sobre no materializa
│       │     el analito que la respuesta discute
│       ├── SALVAGE INSUFICIENTE .......................... CONFIRMADO
│       │     `if not kept: raise first_rejection` -> con 1 solo claim
│       │     (materialized_fact_count=1) no hay nada que salvar;
│       │     además hay comprobaciones globales posteriores que no cubre
│       ├── EL REPAIR NO REPARA ........................... CONFIRMADO
│       │     repetición ×10: 0/9; 11 de 19 turnos repiten EL MISMO detalle;
│       │     el repair prompt crece sólo +2,48 % (mediana) -> aporta poca
│       │     información nueva. QUÉ aporta exactamente: NO_OBSERVABLE
│       └── SEGURIDAD (rechazo correcto) .................. 7 de 133 (5,3 %)
│
└── COSTE SECUNDARIO .................... 148 s (3,0 %)
    ├── backend, validación, persistencia, red ... 18 s (0,4 %)
    ├── load del modelo .......................... 73 s (1,5 %)
    ├── RAG ...................................... 8 activaciones, 183-655 ms
    └── cola ..................................... mediana 0 ms  DESCARTADO
```

## Eficacia de cada etapa (medida)

| Etapa | Resultado |
|---|---|
| 1.ª generación válida | 53 de 133 llamadas; **1 de 10** en el experimento controlado |
| 2.ª llamada (repair) | **8 valid / 16 invalid / 10 repairable** de 34 |
| 3.ª llamada (último recurso) | **6 valid / 20 invalid** de 26 |
| Desenlace de los 34 turnos con repair | **17 OK / 17 fallo** |
| Tokens desperdiciados | **35.502 de 55.562 = 63,9 %** |
