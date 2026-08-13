# 10 · Referencias bibliográficas y anexos

**Estado: 🟡** Las referencias están en formato IEEE y bien construidas. Los anexos A–D son
sólidos. Falta el Anexo E y hay que auditar la bibliografía después de insertar las secciones
nuevas.

Acciones: `A-REF-01`, `A-REF-02`, y las dos filas de riesgo señaladas desde el Capítulo II.

---

## A-REF-01 · Auditoría de la bibliografía

El documento usa **IEEE numérico** con citas `[n]` resueltas por marcador interno. Es lo correcto:
el manual exige formato IEEE (p. 3 y p. 14) y el IEEE numera por orden de aparición.

> ⚠️ **Contradicción en el propio manual.** En la p. 14 pide que las referencias estén «ordenadas
> alfabéticamente», lo cual es incompatible con la numeración por orden de aparición del IEEE.
> **Recomendación: mantener IEEE numérico** —es lo que exige la instrucción de formato, que es más
> específica— y confirmarlo con el asesor. Si insistiera en el orden alfabético, la solución de
> menor daño es añadir un índice alfabético de autores como apéndice, **sin renumerar** la lista
> principal: renumerarla rompería todas las citas del cuerpo.

### Checklist de auditoría (ejecutar DESPUÉS de insertar §1.1.3.7, §3.11, §5.9, §5.10, §6.6 y §6.8)

- [ ] Cada cita `[n]` del cuerpo resuelve a una entrada existente.
- [ ] Cada entrada de la lista está citada al menos una vez en el cuerpo.
- [ ] La numeración sigue el orden de primera aparición tras insertar las secciones nuevas.
      **Insertar §1.1.3.7 en el Capítulo I desplaza toda la numeración posterior**: es el cambio
      de mayor riesgo mecánico de toda la revisión. Hacerlo con la función de referencias
      cruzadas del procesador de textos, no a mano.
- [ ] Ninguna fuente es Wikipedia ni un blog sin autoría reconocida (el manual lo prohíbe
      explícitamente).
- [ ] Las fuentes con DOI lo llevan; las que son en línea llevan fecha de último acceso.
- [ ] Los títulos en inglés conservan mayúsculas y cursivas según IEEE.

### Referencias nuevas requeridas

**Para §1.1.3.7 (marco teórico del rendimiento de inferencia) — mínimo cinco:**

1. Análisis *roofline* aplicado a inferencia de transformadores: régimen limitado por ancho de
   banda de memoria en la fase de decodificación.
2. **La fuente que publica el sobrecosto de la decodificación restringida por gramática.**
   🔴 **Crítica**: §6.8.3 la refuta cuantitativamente. Refutar una fuente que no está citada es
   indefendible; la cita tiene que ser exacta y verificable.
3. Documentación técnica de la arquitectura NVIDIA A100 (ancho de banda nominal de 2 039 GB/s en
   la variante SXM4 de 40 GB). Una *datasheet* sirve: el manual las acepta como fuente primaria.
4. Cuantización de modelos de lenguaje y su efecto en tamaño efectivo y calidad.
5. Pre-registro de hipótesis como práctica metodológica contra la reinterpretación posterior de
   resultados.

**Para §3.11 y §6.8 (métodos estadísticos) — mínimo tres:**

6. Wilson, sobre el intervalo de confianza para proporciones binomiales, y/o una referencia sobre
   por qué la aproximación normal falla en proporciones próximas a cero.
7. McNemar, sobre el contraste de proporciones pareadas.
8. Wilcoxon, sobre el contraste de rangos con signo. *(Verificar si ya está citado a propósito de
   la validación clínica; si lo está, reutilizar la entrada, no duplicarla.)*

**Para §6.8.6 (kappa):** verificar si la referencia de Cohen ya empleada en §6.3 y §6.4.5 cubre el
uso del coeficiente para el acuerdo entre corridas. Probablemente sí; reutilizarla.

---

## A-REF-02 · 🔴 Anexo E — Evidencia de la campaña de recaracterización

**No existe y hace falta.** Los anexos A–D siguen el mismo patrón: cada resultado importante del
Capítulo VI tiene su respaldo documental. §6.8 sería el único resultado sin anexo.

📄 Estructura propuesta y manifiesto:
[`anexo_E_recaracterizacion/README.md`](anexo_E_recaracterizacion/README.md)

Fila para la Lista de Anexos:

| Anexo | Título | Contenido principal |
| :--- | :--- | :--- |
| Anexo E | Evidencia de la campaña de recaracterización del *runtime* conversacional | Pre-registro firmado con su compendio, tablero de las diez hipótesis, procedencia criptográfica de cada artefacto fuente, manifiesto de figuras y tablas, registro de verificación con la aserción que falla declarada, y paneles de ausencia. |

---

## Anexos existentes — estado

| Anexo | Contenido | Estado | Acción |
| :--- | :--- | :---: | :--- |
| A | Matriz de riesgos actualizada | 🟡 | Añadir dos riesgos (abajo) |
| B | Evidencia de validación clínica | 🟢 | Sin cambios |
| C | Evidencia de validación del asistente LLM/RAG | 🟡 | Añadir la batería de contenido y los datos de agosto |
| D | Instrumento y resultados de usabilidad | 🟢 | Sin cambios |
| **E** | **Campaña de recaracterización** | 🔴 | **Crear** |

### Anexo A — dos riesgos que faltan

La matriz cubre riesgos técnicos, clínicos, documentales, de LLM/RAG, usabilidad, privacidad,
vigilancia y despliegue. No cubre los dos que se materializaron o quedaron vivos en agosto.

> **Fila propuesta R-14 · Indisponibilidad del nodo de inferencia**
>
> | Descripción | El nodo de inferencia opera sobre una instancia interrumpible; el proveedor puede reclamar la capacidad sin previo aviso, y no existe mecanismo automático de rearranque. Durante el desarrollo se registró además un evento real de agotamiento de capacidad zonal. |
> | Probabilidad / Impacto | Alta / Medio |
> | Respuesta | **Mitigar.** La arquitectura aísla el nodo de inferencia, de modo que su caída no afecta al análisis hematológico, la consulta de resultados ni el historial. |
> | Señal de activación | El servicio conversacional deja de responder mientras el resto de la plataforma permanece operativa. |
> | Plan de acción | Rearranque manual del nodo; verificación del estado con antelación a cualquier demostración, dado que el arranque en frío supera los dos minutos; a medio plazo, incorporar un vigilante de rearranque automático. |
> | Responsable | Operación / despliegue |

> **Fila propuesta R-15 · Deriva entre el modelo sellado y el instalado**
>
> | Descripción | El modelo de lenguaje de la configuración anterior permanece instalado en el nodo de inferencia y la comprobación presente en el código no impide su uso, de modo que una configuración errónea podría servir respuestas de un modelo distinto del declarado. |
> | Probabilidad / Impacto | Baja / Alto |
> | Respuesta | **Mitigar.** Verificación del identificador de modelo en cada respuesta emitida; el arranque a prueba de fallos valida el compendio contra el manifiesto de versión. |
> | Señal de activación | Una respuesta registrada cuyo identificador de modelo difiere del sellado. |
> | Plan de acción | Retirar el modelo obsoleto del nodo; convertir la comprobación de identidad en una guarda bloqueante y no solo en una verificación posterior. |
> | Responsable | Backend / despliegue |

### Anexo C — ampliar con la evidencia de agosto

El anexo recoge hoy los CSV y JSON de red-teaming, las baterías A–E, robustez, memoria,
consistencia, rúbricas y evaluación veterinaria. Añadir:

- **Batería de contenido sustantivo**, siete corridas más sondas, con pregunta, respuesta, etapas
  atravesadas, razón de reparación y latencia por turno:
  `validacion_llm/resultados/rondas45_2026-08-10/` (`bateria_ronda4.jsonl`,
  `bateria_ronda5_fresh.jsonl`, `bateria_ronda5_test5.jsonl`, `bateria_ronda6.jsonl`,
  `bateria_a100.jsonl`, `bateria_cierre.jsonl`, `sonda_final.jsonl`).
- El validador y la sonda que las procesan (`validar_45.py`, `sonda.py`), que documentan el
  criterio operativo de «contenido real».

> **Nota de privacidad antes de anexar.** Los ficheros de trazas contienen preguntas y respuestas
> completas. Verificar que no incluyen identificadores de mascota, propietario ni clínica antes de
> incorporarlos al documento entregable. El fixture usado en la campaña es de prueba —una mascota
> ficticia con datos de ensayo—, pero **eso hay que comprobarlo, no suponerlo**, para cada fichero
> que se anexe.

---

## Checklist de cierre de este bloque

- [ ] Anexo E creado según `anexo_E_recaracterizacion/README.md`.
- [ ] Fila del Anexo E añadida a la Lista de Anexos.
- [ ] Riesgos R-14 y R-15 añadidos al Anexo A (y a la Tabla de §2.4 si duplica contenido).
- [ ] Anexo C ampliado con la batería de contenido, previa revisión de privacidad.
- [ ] Ocho referencias nuevas incorporadas en formato IEEE.
- [ ] Numeración de citas verificada de extremo a extremo tras insertar §1.1.3.7.
- [ ] Confirmado con el asesor el criterio IEEE numérico frente a la indicación de orden
      alfabético del manual.
