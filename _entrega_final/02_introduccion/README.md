# 02 · Introducción, objetivos, justificación y limitaciones

**Estado: 🟢 alineado.** Este es el bloque más sano del documento. No contradice al sistema real
en ningún punto sustantivo y no requiere reescritura.

Acción única: `A-INT-01`.

---

## Lo que está bien y no hay que tocar

- **Antecedentes del problema.** El planteamiento —el propietario recibe una lista de valores sin
  síntesis interpretativa; los analizadores IDEXX y Mindray solo marcan valores fuera de rango—
  sigue siendo exacto y está bien citado.
- **Antecedentes del proyecto.** Correcto.
- **Descripción del problema.** Correcta.
- **Planteamiento inicial de la solución.** Cumple lo que pide el manual (p. 5): explica la
  solución **sin** meter algoritmos, componentes ni tecnologías. Verificado: no menciona XGBoost
  ni Ollama. ✅
- **Objetivos.** Un objetivo general y cinco específicos. El manual recomienda «un mínimo de dos
  y máximo cuatro» objetivos específicos (p. 5). **Hay cinco.**
  → Ver la nota de riesgo más abajo.
- **Justificación.** Cubre conveniencia, relevancia social, implicaciones prácticas y valor
  teórico. ✅

---

## ⚠️ Nota de riesgo: cinco objetivos específicos frente al máximo de cuatro

El manual dice, textual: *«se recomienda un mínimo de dos (2) y máximo cuatro (4)»*. El documento
tiene OE1…OE5. Es una **recomendación**, no una prohibición, y los cinco están demostrados como
cumplidos en la Tabla 7.1, que es lo que el manual exige de verdad («todos los objetivos
específicos enunciados deben de demostrarse completados en el proyecto»).

**Recomendación: no tocar.** Fundir OE4 (vigilancia) con OE3 (portal) para bajar a cuatro
debilitaría la Tabla 7.1 y obligaría a reescribir §7.2. El coste de dejarlo en cinco es, como
máximo, un comentario del asesor; el coste de fundirlos es reescribir tres secciones. Si el
asesor lo exige, la fusión de menor daño es OE3+OE4 bajo «portal ciudadano con visualización
individual y comunitaria».

---

## A-INT-01 · Añadir una limitación de infraestructura

**Localización:** sección «Limitaciones del proyecto», al final de la lista.

El manual pide en esta sección los elementos que «pueden afectar al desarrollo del proyecto
siempre que el estudiante no tenga el control por fuerzas mayores» y da como ejemplo textual
«restricción por capacidad informática del equipo». El proyecto tiene hoy exactamente ese caso, y
no está declarado.

> **Texto propuesto para añadir:**
>
> «El componente conversacional del sistema requiere aceleración por unidad de procesamiento
> gráfico para operar con tiempos de respuesta aceptables. El equipo no dispone de hardware
> propio con esa capacidad, por lo que dicho componente se ejecuta sobre una instancia de
> cómputo con GPU contratada bajo la modalidad *spot* o interrumpible, cuya disponibilidad
> depende de la capacidad excedente del proveedor de nube y puede ser reclamada sin previo
> aviso. Durante el desarrollo se registró además un evento real de agotamiento de capacidad
> zonal que impidió temporalmente el arranque de varias familias de máquinas. En consecuencia,
> la disponibilidad continua de la capa conversacional queda fuera del control del equipo y el
> proyecto no contempla un esquema de alta disponibilidad para dicho componente.»

Evidencia: `deploy/gpu/switch-to-a100.sh`, `RESUMEN_PARA_EQUIPO_2026-08-11.md` §3
(evento de capacidad zonal, prod degradada temporalmente a `e2-standard-4`),
commit `f9deedb` (migración de zona a `us-central1-c`).

Esta limitación es la que después sostiene:
- §2.6.1 — el entorno de demostración debe prever la contingencia.
- §7.3 — la limitación operativa correspondiente.
- §7.7 — la sostenibilidad económica del *runtime*.

---

## Verificación cruzada de objetivos ↔ evidencia

Antes de cerrar el documento, confirmar que cada objetivo específico sigue teniendo evidencia
viva. Estado al 12 de agosto de 2026:

| Objetivo | Evidencia declarada en §7.2 | ¿Sigue vigente? |
| :--- | :--- | :---: |
| OE1 · corpus estructurado | Corpus IDEXX + 1 301 DAP + 43 características | ✅ |
| OE2 · modelo multietiqueta | 7 etiquetas, PR-AUC 0,9529, κ 0,629 | ✅ |
| OE3 · portal ciudadano | App con resumen, carga, revisión, resultado, historial, biblioteca, chat + usabilidad n = 44 | ✅ |
| OE4 · vigilancia comunitaria | Reporte poblacional funcional | ⚠️ la sección de resultados que lo demuestra **no existe** → §6.6 |
| OE5 · capa conversacional con *guardrails* | Seguridad 30/30, exactitud 83,3 %, κ 0,841, *prompt injection* 61 → 1 | ⚠️ cifras de julio → actualizar con §6.9 |

Las dos casillas de advertencia se resuelven en `../08_capitulo_vi_resultados/`.
