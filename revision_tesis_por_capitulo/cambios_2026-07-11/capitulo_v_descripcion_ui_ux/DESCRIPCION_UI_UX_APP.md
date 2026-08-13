# HemoVet — Descripción de la interfaz (UI) y la experiencia de usuario (UX)

> Descripción extensiva de la aplicación a nivel de interfaz y experiencia, tomada del
> código real de la interfaz principal `frontend_4` (React 19 + TypeScript + Vite, con
> TanStack Router/Query, React Aria, React Hook Form + Zod, Chart.js y MapLibre).
> Sirve de insumo para el Capítulo V (Desarrollo) y el Capítulo II/IV (solución y diseño).

---

## 1. Filosofía de diseño

La app es una **plataforma ciudadana** para que el dueño de un perro convierta un hemograma
en información comprensible, sin pretender diagnosticar. Toda la interfaz se construye
alrededor de tres principios que se repiten en cada pantalla:

1. **Orientar, no diagnosticar.** Un aviso de límites clínicos es persistente y omnipresente.
2. **Revisión humana obligatoria.** El usuario siempre confirma los valores extraídos antes
   de que el modelo los use.
3. **Privacidad por diseño.** La vigilancia comunitaria es agregada; nunca muestra
   direcciones ni ubicaciones exactas.

El tono visual es **clínico-amable**: limpio, con abundante espacio en blanco, tarjetas
suaves, azules teal como color de marca y lenguaje no técnico ("En rango", "Atención",
"Prioridad" en lugar de jerga).

## 2. Sistema visual (design tokens)

La identidad se define con variables CSS, lo que da consistencia total y soporte nativo de
tema claro/oscuro.

- **Tipografía:** títulos en *Lexend* (variable, muy legible) y cuerpo en *Source Sans 3*.
  Datos numéricos y fuentes citadas en monoespaciada.
- **Paleta (modo claro):** lienzo gris muy claro (`#f4f7f8`), superficies blancas, texto
  azul-petróleo oscuro (`#172a32`). Color primario **teal/azul** (`#176b87`). Estados
  semánticos: éxito verde, advertencia ámbar, peligro rojo terroso, info azul — cada uno con
  su variante "soft" para fondos.
- **Modo oscuro:** invierte a lienzo casi negro (`#111719`) con superficies grafito y
  primarios aclarados (`#70bdd2`) para mantener contraste. Se activa por preferencia del
  sistema o manualmente (`ThemeToggle`).
- **Forma:** tarjetas con bordes redondeados y una sombra sutil (`0 10px 28px`), bordes de
  1px en gris frío. Nada estridente.
- **Layout base:** barra lateral de 220px (colapsable a 72px), topbar de 64px y barra de
  navegación móvil de 66px.

## 3. Estructura de navegación (el "shell")

El armazón (`AppShell`) es un layout de tres zonas:

**Barra lateral izquierda** (colapsable con un botón de chevron):
- Marca "HemoVet · Orientación canina" arriba (logotipo con una "H").
- Navegación principal con íconos: **Resumen, Nuevo hemograma, Mascotas, Vigilancia,
  Asistente, Biblioteca**.
- Si el rol es `admin`, aparece además **Panel técnico**.
- Pie con: toggle de tema, **Límites del sistema** (escudo) y botón de **Cerrar/Iniciar
  sesión**.

**Topbar superior:**
- Botón hamburguesa (solo móvil) para abrir la lateral como panel deslizante.
- **Contexto de ruta:** muestra el nombre de la sección actual.
- **Selector de mascota activa:** avatar + `select` que cambia la mascota en foco de forma
  global (persiste en toda la app vía `PetContext`).
- **Botón de cuenta:** inicial del usuario, nombre y rol ("Propietario" / "Administrador" /
  "Modo invitado · Temporal"), con ícono de ajustes.

**Barra inferior móvil:** accesos rápidos a las 4 primeras secciones (Resumen, "Analizar",
Mascotas, Vigilancia) + botón "Más" que abre la lateral.

Detalle fino: hay un **skip link** ("Saltar al contenido principal") para accesibilidad por
teclado, y el ítem activo se resalta con una clase específica.

## 4. Capa de seguridad clínica (omnipresente)

Justo debajo de la topbar, en **todas** las páginas, va la **SafetyBar**: una franja con
escudo que dice *"HemoVet ofrece orientación educativa sobre hemogramas caninos. No reemplaza
el juicio ni la evaluación de un médico veterinario"* + enlace "Ver límites". Es un
`role="note"` fijo, no descartable — decisión deliberada para el contexto médico.

## 5. Onboarding (tour guiado)

Un `TourOverlay` da un recorrido de **8 pasos** la primera vez, anclado a elementos reales
vía atributos `data-tour`: Bienvenida → Panel de resumen → Cargar un hemograma → Registrar
mascotas → Vigilancia comunitaria → Asistente con IA → Biblioteca clínica → "¡Todo listo!".
Resalta cada zona de la interfaz en su sitio.

## 6. Modo invitado y gating por permisos

La app distingue tres estados de sesión y **degrada con elegancia** en vez de bloquear en
seco:

- **Invitado (sin cuenta):** puede subir un hemograma, revisar valores y ver el resultado del
  modelo — pero **no se guarda nada**. El dashboard invitado muestra tarjetas con "Análisis
  puntual: Disponible" frente a "Historial: Bloqueado", "Mapa y Chat: Requieren cuenta".
- **Con cuenta pero sin mascota:** puede analizar sin asociar, con invitación a registrar
  mascota para tener historial.
- **Con cuenta y mascota:** experiencia completa.

Las funciones privadas (Chat, Mapa) usan un componente `PrivateFeatureGate` que, en lugar de
un error, muestra una tarjeta explicando qué desbloquea iniciar sesión.

## 7. Las pantallas, una por una

### 7.1 Autenticación (Login / Registro)

Pantalla partida en dos: a la izquierda el **panel de formulario** (marca, "Revisa la
información de tu mascota", campos con íconos, mostrar/ocultar contraseña, botón primario a
ancho completo y **"Entrar en modo invitado"** como alternativa secundaria); a la derecha un
**panel de contexto** azul oscuro que comunica el propósito ("Convierte un hemograma canino
en información más comprensible") con una lista de beneficios. Limpio, centrado, sin
distracciones.

### 7.2 Panel / Resumen (Dashboard)

Es la portada tras entrar. Saludo personalizado ("Hola, revisemos a *[mascota]*") y botón
primario "Nuevo hemograma". Se organiza en dos columnas:

- **Columna principal:** grilla de 3 **tarjetas-métrica** (Hemogramas guardados, Último
  análisis con fecha, Vigilancia comunitaria activa/inactiva); un **panel de último
  resultado** con el hallazgo principal, resumen, "Calidad de lectura %", nº de hallazgos y
  acciones "Abrir resultado" / "Copiar resumen"; y una lista de **hemogramas recientes**
  (últimos 3) enlazables con badge de estado.
- **Columna lateral:** tarjeta de perfil de la mascota activa (avatar, raza, edad, peso, zona
  privada), accesos rápidos (Historial, "Preguntar con contexto", Buscar definición) y un
  **recordatorio clínico** ("Antes de decidir, comparte el informe con tu veterinario").

### 7.3 Flujo de análisis (el corazón de la app)

La página `AnalysisPage` guía por un **stepper de 3 pasos** (Archivo → Revisión → Resultado)
con estados visuales done/active/pending (check al completar). El área tiene una columna
principal de trabajo y una lateral de contexto.

1. **Subir (upload):** selector de modo ("Cargar archivo" vs "Ingreso manual"). En modo
   archivo, una gran **zona de arrastre** (drop-area) que acepta PDF, CSV, Excel e imágenes
   (JPG/PNG/TIFF/WebP), con nota de que *no* procesa radiografías ni frotis. Muestra el
   archivo seleccionado con tamaño y badge "Listo", y botón "Extraer valores".
2. **Extrayendo:** estado de proceso con spinner, texto explicativo ("Buscando parámetros,
   unidades y comentarios") y una barra de progreso.
3. **Revisión (obligatoria):** aquí vive el principio de "revisión humana". Muestra el eyebrow
   **"Revisión humana obligatoria"** y badge "Pendiente". Dos **tablas de parámetros** lado a
   lado (series roja/blanca/plaquetaria) con columnas Parámetro / Unidades / Valor detectado,
   editables. Los campos principales llevan asterisco (*). Si hay advertencias de extracción,
   se muestran en línea. Si el usuario tiene cuenta pero no mascota, aparece un prompt para
   "Crear mascota" (autocompletable con metadatos detectados del archivo). Botones "Volver" /
   "Confirmar y analizar". Valida que haya al menos 3 valores principales y que todo sea
   numérico.
4. **Analizando:** otro estado de proceso ("El modelo revisa relaciones entre las series
   roja, blanca y plaquetaria").
5. **Resultado:** si se asoció a mascota, navega a la página de resultado persistido; si no,
   muestra un **resultado temporal** en la misma pantalla.

La **columna lateral** muestra el contexto (mascota, raza, "Especie admitida: Canina", si se
guardará o es temporal, checkbox para asociar) y una nota de "La calidad del archivo importa".

### 7.4 Resultado del análisis

El resultado (temporal o persistido) se compone de:

- **Resumen** con ícono, hallazgo principal como título y badge "Guardado/No guardado". Si no
  se guardó, un aviso ámbar explica por qué (modo invitado o sin mascota).
- **Hallazgos** ("Qué observó el sistema"): tarjetas por hallazgo con marcador de color y
  badge de severidad — **Prioridad** (rojo), **Atención** (ámbar), **Informativo** (neutro).
- **Valores confirmados** ("Datos usados por el modelo"): tabla con Parámetro /
  Resultado+unidad / Referencia (min-max) / Lectura con badge **En rango / Bajo / Alto /
  Crítico**.
- Acciones: "Analizar otro hemograma" y, en invitado, "Crear cuenta".

### 7.5 Asistente (Chat con RAG)

Requiere sesión. Layout de dos columnas:

- **Panel de contexto (izquierda):** un `radiogroup` para elegir **qué información puede usar
  el asistente** — "Información general", "Hemograma seleccionado", "Hemograma histórico" (con
  selector del hemograma concreto por fecha). Y una tarjeta de **"Límites activos"**: *no
  emite diagnósticos, no indica medicamentos/tratamientos/dosis, una urgencia requiere
  atención veterinaria*.
- **Panel de chat (derecha):** cabecera "Asistente HemoVet · RAG con corpus veterinario
  local" con badge del contexto actual. Estado vacío con **sugerencias clicables** ("¿Qué
  significa tener los leucocitos altos?"). Los mensajes se transmiten **en streaming** (SSE):
  mientras responde, muestra etapas legibles ("Validando la consulta…", "Buscando contexto
  relevante…", "Preparando una respuesta segura…", "Verificando la respuesta…"). Cada
  respuesta del asistente puede incluir: **"Datos utilizados"** (los `case_facts` del
  hemograma con checks), un desplegable **"Ver fuentes"** (libro > tema, del corpus) y
  **advertencias**. Composer con textarea (máx 2000 caracteres) y botón enviar. Manejo de
  error elegante: si falla a mitad, conserva lo parcial y añade el mensaje de error.

### 7.6 Vigilancia comunitaria (mapa)

Requiere sesión. Encabezado con selector de periodo (30/90 días). Una franja de método
destaca la **privacidad**: *"Una zona solo aparece cuando al menos 3 mascotas han aportado
información con consentimiento. Nunca mostramos direcciones ni ubicaciones exactas"*. Debajo,
layout de mapa (MapLibre) con **leyenda de intensidad** (pocos/varios/más registros) e
indicador "Información actualizada" (se refresca por SSE o polling cada 25 s). Un **panel de
zonas** lista cada zona con su hallazgo más frecuente, conteos y badge de intensidad. Para
accesibilidad hay una **"alternativa textual"** — tabla equivalente al mapa — y un panel de
"Actividad reciente" por periodo. Estados vacíos honestos ("Ninguna zona cumple todavía los
mínimos… para proteger la privacidad").

### 7.7 Mascotas / Perfil / Historial

Gestión de mascotas con `PetFormModal` (crear/editar, con foto y un `ResidenceMapPicker` para
zona aproximada con consentimiento). El historial usa `HistoryChart` (Chart.js) para la
evolución temporal de valores.

### 7.8 Biblioteca / Glosario y Límites

- **Biblioteca:** glosario buscable de términos hematológicos (definiciones en lenguaje
  llano), con páginas de definición individuales.
- **Límites del sistema:** página dedicada que explicita el alcance clínico y lo que el
  sistema **no** hace — el destino del enlace "Ver límites" de la SafetyBar.

### 7.9 Cuenta y Panel técnico

- **Cuenta:** preferencias del usuario.
- **Panel técnico (solo admin):** métricas/estado del sistema.

## 8. Estados de la interfaz (loading / vacío / error)

Muy cuidados y consistentes, con tres componentes reutilizables:

- **LoadingState** — spinner + etiqueta ("Preparando el resumen").
- **StatePanel** — pantallas de error/vacío con ícono, título, descripción, tono y acción
  "Reintentar".
- **StatusBadge** — sistema de badges semánticos (éxito/atención/peligro/info/neutro) que
  unifica todo el lenguaje de estado.

Nunca hay un error "crudo": cada fallo de red ofrece reintentar y cada vacío explica qué hacer.

## 9. Accesibilidad

Punto fuerte y verificable (usan axe-core, Playwright, Vitest): `skip-link`, `sr-only` para
lectores de pantalla, `aria-live="polite"` en el chat, `role="radiogroup" / "note" / "alert"`,
foco visible (`:focus-visible`), tablas con `scope="row"`, regiones scrollables enfocables por
teclado, objetivos táctiles de mínimo 44px y respeto a `prefers-reduced-motion` (desactiva
animaciones). Controles construidos sobre React Aria Components.

## 10. Responsive

Mobile-first desde 320px. En móvil, la lateral se vuelve panel deslizante y aparece la barra
inferior de navegación; las grillas de tarjetas y las tablas colapsan a una columna con scroll
horizontal contenido (`max-width:100%`). El diseño usa flexbox/grid con `min-width:0` por todas
partes para evitar desbordes.

---

## Síntesis

Es una app clínica-ciudadana, cuidada y accesible, cuyo ADN de UX es la **seguridad y la
transparencia**: el usuario siempre ve los límites, siempre confirma los datos antes de que el
modelo actúe, siempre puede ver las fuentes del chat y su privacidad geográfica está protegida
por diseño.

## Anexo — Rutas y archivos de referencia (para trazabilidad en la tesis)

| Elemento | Archivo (`frontend_4/src/`) |
| --- | --- |
| Armazón y navegación | `app/AppShell.tsx` |
| Sesión / login / modo invitado | `app/AuthContext.tsx`, `pages/LoginPage.tsx`, `pages/RegisterPage.tsx` |
| Mascota activa global | `app/PetContext.tsx` |
| Tema claro/oscuro | `app/ThemeContext.tsx`, `components/ThemeToggle.tsx` |
| Onboarding | `app/TourContext.tsx`, `components/TourOverlay.tsx` |
| Aviso de límites | `components/SafetyBar.tsx`, `pages/LimitsPage.tsx` |
| Dashboard | `pages/DashboardPage.tsx` |
| Flujo de análisis | `pages/AnalysisPage.tsx`, `pages/AnalysisResultPage.tsx` |
| Chat RAG | `pages/AssistantPage.tsx`, `domain/chatStream.ts` |
| Vigilancia | `pages/SurveillancePage.tsx`, `components/SurveillanceMap.tsx` |
| Mascotas e historial | `pages/PetsPage.tsx`, `pages/PetDetailPage.tsx`, `pages/HistoryPage.tsx`, `components/HistoryChart.tsx` |
| Biblioteca | `pages/LibraryPage.tsx`, `pages/DefinitionPage.tsx` |
| Estados de UI | `components/LoadingState.tsx`, `components/StatePanel.tsx`, `components/StatusBadge.tsx` |
| Gating de funciones | `components/PrivateFeatureGate.tsx`, `components/GuestModeModal.tsx` |
| Design tokens y estilos | `styles.css` |
