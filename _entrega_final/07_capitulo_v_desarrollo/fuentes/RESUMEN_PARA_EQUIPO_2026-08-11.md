# HemoVet — Resumen para el equipo: qué pasó desde tu test de 45 turnos

**Para:** el autor de `test_domingo/pruebas_conversacion_3modos_2026-08-09`
**Período:** 9-11 de agosto de 2026 · **Commits:** `663094b` … `3e54b2b` (14 desplegados)

## 1 · Tu test fue el disparador

Tu batería midió lo que la nuestra no medía: **¿la respuesta contiene algo
después de quitar el andamiaje?** Resultado: 13/45 turnos con contenido real,
0/15 en historial, y turnos que devolvían HTTP 200 con solo la frase de
derivación. Tu arnés era válido (lo verificamos) y las cuatro fallas que
señalaste tenían mecanismo exacto en el código:

1. **Ninguna puerta exigía sustancia**: un sobre con una sola claim
   CONVERSATIONAL pasaba todas las validaciones vacuamente, y el requisito de
   derivación se satisfacía por construcción cuando la respuesta ERA solo la
   derivación.
2. **El router re-clasificaba la pregunta sin expandir** (la seguridad juzga
   la expandida): las elipsis («¿De qué está compuesto?», «¿Para qué
   sirven?») caían al fallthrough OUT_OF_DOMAIN y se rechazaban.
3. **El hallazgo del historial era el del estudio viejo**: los estudios
   llegan cronológicos ascendentes y el backstop tomaba la primera
   observación no cubierta → tu «Sin patrones» del 17-dic sombreando la
   Policitemia del 18-dic. (Tu hallazgo, textual.)
4. **Instrucciones en conflicto**: la de selected/history presuponía «el
   parámetro solicitado» y terminaba mandando derivar → para preguntas sin
   parámetro el modelo emitía solo el cierre.

## 2 · Qué se construyó (rondas 4-6)

**Puerta de contenido** (`content_free_answer`): el sobre que solo deriva es
inválido — y las cláusulas de incapacidad («no puedo confirmar») y el eco de
la pregunta («Me preguntas si…») no cuentan como contenido.

**Completado determinista** — el principio rector fue del dueño: *todo lo que
la BD ya sabe se responde desde la BD, y se arregla solo la parte dañada de la
respuesta, nunca se regenera entera*. Hoy salen por código, a costo cero de
GPU, verificados con los mismos matchers del validador:

- el valor/unidad/rango/estado del parámetro en discusión;
- los extremos de una serie y el **resumen de cambios** («RBC: subió de 7.84
  a 8.93 10^12/L; el más reciente está alto» — tu «¿Qué cambió entre los
  estudios?» responde así ahora);
- el inventario del historial (conteo + fechas);
- el patrón/hallazgos registrados (encabezando la respuesta) y, si no hay
  nada anormal, el «no hay hallazgos registrados» honesto + precaución de
  vigilar signos;
- fecha, laboratorio, analizador y lista de parámetros del estudio;
- la frase de derivación faltante y la lista de preguntas para el
  veterinario (tu SEL-12, que moría en TODAS las corridas, cerró así).

**Elipsis y seguimientos**: el resolutor expande las preguntas con sujeto
omitido y las de propiedad («¿qué unidad tiene?» resuelve el parámetro
recordado), el router clasifica el standalone, y un seguimiento sin evidencia
positiva de fuera-de-dominio continúa por la ruta educativa.

**Reparación compacta** para lo que sí regenera, con guardas de raíz: negar
la derivación o declarar falsa incapacidad obliga a reescribir (completarlo
enmascararía el error).

**Instrumentación**: el entailment de citas registra cada veredicto (score) y
cada timeout — la evidencia que faltaba para ajustar el umbral. Y el prune de
disco corre por presión (≥70 %), tras el segundo incidente de disco lleno.

## 3 · La migración a A100 (madrugada del 11)

La L4 se reemplazó por una **A100-SXM4-40GB spot** en la misma zona:

- IP interna `10.128.0.3` promovida a estática y heredada — **el backend no
  cambió ni una línea**.
- La cadena fail-closed estaba anclada al hardware en dos capas
  (`validate-runtime.sh` y `validate-host.sh` exigían «NVIDIA L4») y apagó la
  máquina dos veces — como está diseñada. Se parchearon ambas (aceptan L4 y
  A100, el rollback sigue validando), manifest regenerado, bundle instalado
  por cirugía de disco offline con `hemovet-rescate`.
- En medio: un evento de capacidad zonal real (ni e2/n1/n2d/t2d arrancaban);
  prod quedó temporal en `e2-standard-4` — pendiente devolverla a `-8`.
- Bonus: la A100 carga el modelo con `context_length` **65536** (4× el tope
  de la L4).

## 4 · Los números, con tu batería como instrumento

| | Tu corrida (9-ago) | Ronda 6 (L4) | **A100 (hoy)** |
|---|---:|---:|---:|
| Turnos con contenido real | 13/45 | 44/45 | 40/45* |
| Muertes | 1 (+13 vacíos) | 1 | **0** |
| Mediana global | ~46 s | 44 s | **17.6 s** |
| selected mediana | 32 s | 68 s | **17.6 s** |
| historial con datos | 0/15 | 15/15 | 12/15* |
| Peor turno | 118 s | 161 s | **65 s** |

\* Los 4-5 turnos flojos por corrida son la lotería K=1 de reparaciones que
caen al last-resort — la clase residual documentada, hoy con la mitad de
castigo. El modelo se conservó (qwen3.6:27b): cuando responde, es exacto —
todas las fallas eran del sistema.

## 5 · Dónde está todo

- **Informe completo**: `CAMBIOS_LLM_RONDA4_2026-08-09.md` (mecanismos,
  decisiones y el bucle batería→análisis→ajuste).
- **Las 7 baterías + sondas** (pregunta, respuesta, etapas, razón de
  reparación, latencia por turno) y el runner del recorrido completo
  (registro → residencia → subida → chat SSE):
  `validacion_llm/resultados/rondas45_2026-08-10/`.
- **Migración GPU**: `deploy/gpu/switch-to-a100.sh` + commit `3e54b2b`.

## 6 · Pendientes señalados

1. Watchdog de re-arranque para la spot (si Google la reclama, queda parada).
2. `hemovet-prod` de vuelta a `e2-standard-8` (corte breve).
3. Leer la telemetría del entailment en la próxima batería → ajustar citas.
4. Matar la lotería residual del last-resort (la clase de ~4-5 por corrida).
5. Subir perfiles de contexto para aprovechar los 65k de la A100.
6. Decisión de producto: ¿se relayan los diagnósticos diferenciales
   guardados en la BD con atribución al sistema?

Tu batería queda como el instrumento oficial de contenido del proyecto —
gracias por construirla.
