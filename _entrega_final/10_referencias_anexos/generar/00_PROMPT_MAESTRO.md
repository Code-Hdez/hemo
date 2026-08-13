# Prompt maestro — referencias bibliográficas y anexos

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~12 000 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona.
No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El bloque completo de **Referencias bibliográficas y Anexos**, listo para pegar en el documento de
tesis: la bibliografía actual reproducida íntegra con las entradas nuevas señaladas, los anexos A
a D con dos ampliaciones, y un **Anexo E completo que hoy no existe**. Un solo documento continuo,
no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota. En agosto de 2026 se migró su *runtime* conversacional
a una unidad de procesamiento gráfico NVIDIA A100 y se caracterizó el cambio con una campaña de
medición de diez hipótesis firmadas antes de medir.

**Las referencias están bien construidas y en formato IEEE. Los anexos A a D son sólidos.** Lo que
falta:

1. **El Anexo E no existe.** Los anexos A–D siguen el mismo patrón: cada resultado importante del
   Capítulo VI tiene su respaldo documental. Con §6.8 incorporada, sería **el único resultado del
   proyecto sin anexo**, y precisamente el que más evidencia tiene detrás.
2. **La matriz de riesgos del Anexo A no cubre dos riesgos** que se materializaron o quedaron vivos
   en agosto: la indisponibilidad de la instancia interrumpible y la deriva entre el modelo sellado
   y el instalado.
3. **El Anexo C no recoge la evidencia de agosto:** la batería de contenido sustantivo que en la
   práctica se convirtió en el instrumento de aceptación del proyecto.
4. **Faltan ocho referencias** que las secciones nuevas de otros capítulos necesitan.

## Las tres reglas que gobiernan todo

### Regla 1 · No inventes ni una sola referencia 🔴

Es la regla absoluta de este bloque, y no admite excepciones ni atajos.

**Una referencia inventada es el único error de todo el documento que un miembro del comité puede
verificar desde su teléfono, en treinta segundos, en mitad de la defensa.** No hay ningún beneficio
que compense ese riesgo.

Por tanto:

- ✅ **Sí:** reproducir literalmente cada entrada de la bibliografía actual, con su número.
- ✅ **Sí:** escribir `[CITA PENDIENTE: análisis roofline aplicado a inferencia de transformadores;
  se necesita un trabajo que establezca el régimen limitado por ancho de banda de memoria en la
  fase de decodificación]`.
- ❌ **No:** escribir una entrada con autor, título, publicación y año que no hayas verificado.
- ❌ **No:** «completar» una referencia parcial adivinando el año o el volumen.

Un marcador honesto se resuelve con una tarde de búsqueda. Una referencia inventada no se resuelve.

### Regla 2 · Un anexo presenta evidencia; no la analiza

Los anexos respaldan lo que el Capítulo VI ya dijo. **No repiten su análisis y no añaden
interpretación.**

- ✅ **Sí:** «Tabla E.5 — Aserciones de recálculo: once ejecutadas, diez coinciden con el valor
  publicado y una no.»
- ❌ **No:** «lo que demuestra la solidez del procedimiento de verificación».

Cada apartado sí necesita **un párrafo introductorio** que diga qué se está mirando: un anexo que
es solo tablas encadenadas no se lee. Los anexos B, C y D ya lo hacen bien; sigue su registro.

### Regla 3 · Lo que no se pudo medir se anexa igual

El Anexo E incluye deliberadamente **la evidencia de lo que falló y de lo que no se pudo medir**:
la aserción de verificación que no coincide, los ejes de la rúbrica que no se pudieron puntuar, los
niveles del esquema de trazas que quedaron vacíos, y las tres limitaciones declaradas de la
ablación.

**Eso no se esconde ni se resume: es lo que acredita que la verificación es real.** Un anexo que
solo publica lo que salió bien no se distingue de uno que no verificó nada.

## Estructura de salida exigida

```
Referencias Bibliográficas              → ÍNTEGRAS + entradas nuevas señaladas

Anexo A. Matriz de riesgos              → ÍNTEGRO + dos filas (R-14, R-15)
Anexo B. Validación clínica             → ÍNTEGRO
Anexo C. Validación del asistente       → ÍNTEGRO + un apartado nuevo
Anexo D. Usabilidad                     → ÍNTEGRO
Anexo E. Campaña de recaracterización   → ANEXO NUEVO COMPLETO (9 apartados)
```

El Anexo E lleva **encabezado de nivel 1**, como los demás, y sus apartados E.1 a E.9 de nivel 2.

## Extensión

El bloque actual tiene ~5 390 palabras. El resultado debe estar entre **7 500 y 8 600 palabras**:
el Anexo E aporta unas 2 000 y las ampliaciones de A y C unas 400.

El Anexo E son 6 a 8 páginas **contando sus tablas**, varias de las cuales son largas y no las vas
a transcribir: irán como marcadores. Así que en palabras de prosa el anexo es más corto de lo que
sugiere su paginación.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
