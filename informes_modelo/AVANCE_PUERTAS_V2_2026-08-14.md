# Avance Puertas v2 — dónde está el entregable y qué dice

> **Trabajo EN CURSO y no terminado.** Dos de las cuatro puertas pre-registradas
> rechazan, y la regla escrita antes de medir dice que no se pasa a la fase
> siguiente.

**Entregable completo:** `~/avance_hemovet_puertas_v2_2026-08-14/`
(fuera del repositorio, con la misma disciplina que
`recaracterizacion_hemovet_a100_2026-08-11`: `PROCEDENCIA.json`,
`TRAZABILIDAD.csv` y `SHA256SUMS`).

**Por dónde empezar:** `07_informes/RESUMEN_EJECUTIVO.md` — dos páginas,
autosuficiente. Después el cuaderno,
`06_analisis/HEMOVET_PUERTAS_V2_AVANCE.ipynb`, que corre con `Restart & Run All`
sin red y sin GPU y verifica los hashes de sus fuentes al arrancar.

---

## Las tres correcciones de método que este trabajo aporta

### 1. La casilla la decide `codigo_error`, no el código HTTP

`[MEDIDO]` El pre-registro §1 lo dice expresamente, y la diferencia **cambia dos
veredictos**: los fallos terminales llevan `codigo_error = invalid_model_output`,
que es el validador propio rechazando una respuesta, no el proveedor caído.
Contarlos por HTTP los manda a la Puerta D —inventando un problema de
infraestructura que no existe— y de paso vacía la Puerta C, que es la que sí
está bloqueando.

La figura **M1** del cuaderno dibuja las dos lecturas sobre los mismos turnos.

### 2. La Puerta S se mide sobre lo publicado, y se verificó desde fuera

`[MEDIDO]` No se aceptó el `validation_status` que el propio backend declara: se
importó su `OutputValidator` y se pasó **en frío** sobre las respuestas
publicadas (`05_derivados/revalidar_publicado.py`). Un turno cuyo primer borrador
propuso un tratamiento y el validador detuvo es un **éxito** del sistema de
seguridad, no un fallo.

### 3. La cadena que lleva a un fallo terminal está en el código, y ahora medida

```
main falla la validación
  → repair (tope 2, y está en el TIPO del campo: CHAT_MAX_GENERATION_ATTEMPTS le=2)
  → repair falla también
  → _last_resort_candidate NO se ejecuta: CHAT_STRUCTURED_OUTPUT_ENABLED=0
  → invalid_output_<motivo> → invalid_model_output → HTTP 502
```

`[MEDIDO]` La última línea se leyó **del proceso desplegado**, no del código.
Lo que sigue sin conocerse es **el texto** que el validador rechazó, no el
mecanismo: `_safe_operational_log_payload` recorta toda cadena a 192 caracteres
antes de escribir cualquier log, por diseño de privacidad clínica.

---

## Qué se instrumentó de nuevo, sin tocar el backend

| Añadido | Qué cierra |
|---|---|
| `cuerpo_error_crudo` **íntegro** | el sobre completo de cada fallo terminal; el arnés viejo hacía `json.loads` y se quedaba con el código |
| `case_facts` completo | permite reproducir en frío los predicados de atribución, que son la mayoría de los rechazos |
| Eventos con marca de tiempo | reparto del tiempo entre cliente y servidor |
| `memoria_contaminada` + huecos | marca los turnos cuyo historial tiene agujeros porque un turno anterior murió |

---

## Trampas confirmadas en esta ventana

1. **El despliegue falla si las VMs están apagadas.** No es un pipeline roto: el
   túnel IAP no tiene destino. Se resolvió **re-ejecutando los jobs fallidos del
   run existente**, sin commit nuevo, para no caer en la trampa del commit vacío.
2. **Encender la GPU sola, esperar por journal, y solo entonces la CPU.**
   Funcionó: arranque validado en 4 min 45 s con `latency_ms≈203102`.
3. **La GPU reconcilia su release al arrancar**, así que aplica la imagen del
   runtime de la release deseada aunque el bundle de arranque sea idéntico. Es
   una fila del sello que cambia y hay que declararla.

---

## Lo que sigue abierto, con su coste

| Hueco | Coste de cerrarlo |
|---|---|
| Persistir el candidato rechazado (cierra los paneles X1 y X2) | ≈ 1 día + una ventana |
| Fijar y registrar `seed` (cierra X7) | ≈ medio día + una ventana |
| Medir la memoria conversacional sin huecos de historial | ≈ 12 min de GPU |
| Atacar la Puerta C desde los datos, no por prompt | su propia puerta |

**Cuatro intentos por la vía del prompt ya fracasaron.** Eso, en sí mismo, es un
resultado: el camino no es avisar mejor al modelo, es no darle la ocasión.
