# Anexo B — Manual de usuario de HemoVet

> Guía de uso de la aplicación para el propietario. Describe el recorrido completo, del registro
> a la descarga del resumen para el veterinario. Basado en la interfaz real (`frontend_4`).
> Recordatorio permanente: **HemoVet orienta, no diagnostica; no sustituye al médico veterinario.**

## B.1. Acceso a la aplicación

1. **Crear cuenta / iniciar sesión.** En la pantalla de entrada, registra tu correo y contraseña,
   o inicia sesión si ya tienes cuenta.
2. **Modo invitado.** Si solo quieres probar el sistema, pulsa "Entrar en modo invitado": puedes
   subir un hemograma y ver el resultado del modelo, pero **no se guardará** ningún dato ni
   historial.

## B.2. Registrar una mascota

Desde "Mascotas" → "Crear mascota", completa nombre, raza, año de nacimiento y peso. Opcionalmente,
puedes indicar una **zona de residencia aproximada** (con tu consentimiento) para el módulo de
vigilancia comunitaria; nunca se guarda tu dirección exacta. Registrar una mascota permite **guardar
el historial** de sus hemogramas.

## B.3. Analizar un hemograma (recorrido de 3 pasos)

La pantalla "Nuevo hemograma" te guía por tres pasos:

1. **Archivo.** Elige "Cargar archivo" y arrastra o selecciona el documento del hemograma (PDF,
   hoja de cálculo o imagen: JPG/PNG/TIFF/WebP). También puedes elegir "Ingreso manual" y transcribir
   los valores. *HemoVet no procesa radiografías, frotis ni estudios bioquímicos.* Pulsa "Extraer
   valores".
2. **Revisión (obligatoria).** El sistema muestra los valores que detectó. **Compara cada dato con
   el documento original y corrígelo si es necesario.** Los campos marcados con asterisco (*) son los
   principales; se necesitan al menos tres para continuar. Este paso es clave: un valor mal leído
   puede cambiar el resultado. Pulsa "Confirmar y analizar".
3. **Resultado.** El modelo procesa el perfil completo y presenta el resultado.

## B.4. Leer el resultado

El resultado se organiza en tres bloques:

- **Resumen:** el hallazgo principal en lenguaje llano, con una etiqueta de si se guardó o no.
- **Hallazgos ("Qué observó el sistema"):** tarjetas con un color y una etiqueta de prioridad —
  **Prioridad** (rojo), **Atención** (ámbar) o **Informativo** (neutro).
- **Valores confirmados:** tabla con cada parámetro, su valor, el rango de referencia y una lectura
  (**En rango / Bajo / Alto / Crítico**).

Puedes **copiar el resumen** para compartirlo con tu veterinario.

## B.5. Usar el asistente (chat)

En "Asistente" puedes hacer preguntas sobre el hemograma. Antes de preguntar, elige **qué información
puede usar**: información general, un hemograma seleccionado o uno del historial. El asistente:

- explica términos, valores y hallazgos con **fuentes** del corpus veterinario;
- **no** emite diagnósticos, **no** indica medicamentos, tratamientos ni dosis;
- te ayuda a **preparar preguntas** para la consulta veterinaria.

Puedes usar las preguntas de ejemplo para empezar.

## B.6. Historial y evolución

Con una mascota registrada, "Historial" muestra sus hemogramas guardados y un gráfico de **evolución
temporal** de los valores, útil para el seguimiento de condiciones crónicas.

## B.7. Vigilancia comunitaria

"Vigilancia" muestra, sobre un mapa de **zonas agregadas**, los hallazgos más frecuentes cerca de tu
zona. Una zona solo aparece cuando al menos **3 mascotas** han aportado datos con consentimiento.
Es información **orientativa y anónima**, no una medida de prevalencia real.

## B.8. Biblioteca y límites

- **Biblioteca:** diccionario de términos hematológicos en lenguaje sencillo.
- **Límites del sistema:** explica con claridad qué hace y qué **no** hace HemoVet.

## B.9. Cuenta y preferencias

Desde el botón de cuenta puedes ajustar tus preferencias y cambiar el **tema claro/oscuro**. La app
es accesible por teclado y compatible con lectores de pantalla.

## B.10. Recomendación final

HemoVet es una herramienta de **orientación y control de calidad**. Ante cualquier hallazgo o duda,
**comparte el informe original y el contexto completo con tu médico veterinario**, que es quien puede
interpretar el estado de salud de tu mascota.
