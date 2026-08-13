# Checklist de formato — entrega física y digital

Fuente: manual EICT Rev. Sept. 2025, «Consideraciones generales» (p. 3–4).
Marcar cada casilla sobre el `.docx (4)` antes de exportar a PDF.

## Tipografía y composición

- [ ] Fuente: Courier, Courier New, **Times New Roman** o Bookman Old Style (una sola en todo el documento).
- [ ] Interlineado 1,5 en todo el cuerpo.
- [ ] Cuerpo 12 pt · subtítulos 13 pt · títulos 14 pt.
- [ ] Texto justificado a izquierda y derecha.
- [ ] Escritura en negro sobre fondo blanco (revisar que ninguna figura arrastre fondo de color).
- [ ] Palabras o nombres en otro idioma **en cursiva** (`prompt`, `prompt injection`, `guardrail`,
      `spot`, `fail-closed`, `roofline`, `prefill`, `decode`, `streaming`, `bootstrap`, `overlay`,
      `flag`, `dashboard`, `feature`, `dataset`, `pipeline`).
- [ ] Solo cuatro niveles de título:
  - [ ] Nivel 1 en MAYÚSCULAS y centrado.
  - [ ] Nivel 2 alineado a la izquierda, mayúscula inicial en palabras principales.
  - [ ] Nivel 3 alineado a la izquierda, mayúscula solo en la primera palabra.
  - [ ] Nivel 4 (si se usa) consistente en todo el documento.

## Márgenes y paginación

- [ ] Superior 2,54 cm.
- [ ] Inferior 3,17 cm.
- [ ] Izquierdo 3,81 cm.
- [ ] Derecho 2,54 cm.
- [ ] Paginación arábiga, **inferior derecha**.
- [ ] Números romanos en: páginas de presentación, portadillas, dedicatorias y agradecimientos.
- [ ] Encabezado de página con el título del trabajo y/o los nombres de los autores (opcional pero
      recomendado; si se usa, en todas las páginas del cuerpo).

## Portada

- [ ] Título completo del proyecto.
- [ ] Integrantes **con sus ID**.
- [ ] Asesor.
- [ ] Formato según Anexo 1 del manual.
- [ ] Lomo (entrega física): título del trabajo + año de entrega.

## Índices

- [ ] Tabla de contenido con **números de página reales** (hoy están vacíos o desactualizados).
- [ ] Lista de Tablas, numeración **consecutiva e independiente**, con página.
- [ ] Lista de Figuras, numeración **consecutiva e independiente**, con página.
- [ ] Lista de Anexos (A, B, C, D **y E**).
- [ ] Lista de Fórmulas — solo si se numeran fórmulas en el cuerpo. Si se incorpora §6.9, entran
      al menos tres: techo de decodificación (ancho de banda ÷ tamaño de modelo), MBU e intervalo
      de Wilson. **Decidir**: o se numeran y se listan, o se dejan en prosa sin numerar.

> ⚠️ **Consistencia de numeración.** El documento mezcla dos esquemas: `Tabla 1…6` (Cap. II) y
> `Tabla 3.1`, `Tabla 6.14` (resto). El manual pide numeración consecutiva por categoría. La
> opción de menor riesgo es **unificar todo a `Tabla N.M`** (capítulo.orden) y renumerar las seis
> primeras como `Tabla 2.1…2.6`. Si se prefiere no tocarlas, dejarlo declarado y consistente,
> pero no mezclar.

## Citación y referencias

- [ ] Modelo **IEEE** en citas y fichas bibliográficas.
- [ ] Toda cita del cuerpo `[n]` resuelve a una entrada existente.
- [ ] Toda entrada de la lista está citada al menos una vez en el cuerpo.
- [ ] Sin Wikipedia ni blogs sin autoría reconocida.
- [ ] DOI o URL con fecha de último acceso donde aplique.
- [ ] Referencias nuevas de §1.1.3.7 y §6.9 incorporadas y numeradas en orden de aparición.

## Figuras y tablas

- [ ] Toda figura tiene pie numerado y descriptivo.
- [ ] Toda tabla tiene título numerado.
- [ ] Las figuras nuevas de §6.9 se insertan en **PDF o SVG** (vectorial), no PNG, para que no
      pixelen en el empastado. Ambos formatos existen en `06_analisis/figuras/`.
- [ ] Verificar legibilidad **en escala de grises** — la campaña ya generó las versiones grises en
      `06_analisis/grises/`; usarlas para revisar antes de mandar a imprimir.
- [ ] Ninguna figura depende solo del color para distinguir series (codificación secundaria por
      marcador o trama).
- [ ] Referencias cruzadas correctas (⚠️ §4.2.5 dice «La Figura 4.5 muestra la topología» y la
      figura contigua está rotulada **Figura 4.6**).

## Entrega

- [ ] Digital en semana 13 del periodo académico, pasada por el control de plagio.
- [ ] Física: un ejemplar empastado, **azul marino con letras doradas**, papel bond 20 blanco.
- [ ] Digital final: una copia en USB.
- [ ] Código fuente registrado en el servidor de control de versiones de la EICT (Anexo II del
      manual). Hoy el repositorio es `xPshycho/hemogramas-proyectoICC` en GitHub — **confirmar con
      el asesor si eso satisface el requisito o hay que espejarlo**.

## Antes de exportar

- [ ] Agradecimientos redactados (una página por estudiante) — hoy solo está el encabezado.
- [ ] Dedicatorias redactadas (una página por estudiante) — hoy solo está el encabezado.
- [ ] Resumen ejecutivo entre 250 y 400 palabras (el manual lo sugiere explícitamente).
- [ ] `Abstract` con la misma extensión y contenido equivalente.
- [ ] Actualizar TOC y listas **al final**, después de aplicar todos los cambios de contenido.
