# Guia general de correccion

## Problema principal

El documento actual mezcla contenido de versiones anteriores del sistema con evidencia nueva. La tesis debe quedar consistente con el programa actual:

- API versionada en `/api/v1`.
- Backend modular con FastAPI, PostgreSQL, SQLAlchemy y Alembic.
- Frontend React/Vite con resumen, vigilancia, chat, biblioteca y evolucion.
- RAG con ChromaDB, FastEmbed, Ollama e ingesta offline de Markdown curado.
- Modelo v3/v4 con 7 etiquetas oficiales de modelo, 2 reglas deterministas y 1 etiqueta excluida.
- Validacion clinica extendida con 4 semanas, 2 medicos y 509 casos evaluables.

## Estructura que debe quedar

La plantilla institucional exige:

1. Preliminares
2. Resumen ejecutivo y Abstract
3. Introduccion
4. Capitulo I - Marco teorico
5. Capitulo II - Solucion propuesta
6. Capitulo III - Metodologia
7. Capitulo IV - Analisis y diseno
8. Capitulo V - Desarrollo
9. Capitulo VI - Analisis de resultados
10. Capitulo VII - Conclusiones y recomendaciones
11. Referencias
12. Anexos

## Regla de trabajo

No mover todos los resultados al Capitulo V. Capitulo V debe describir construccion e implementacion. Capitulo VI debe analizar resultados. Capitulo VII debe cerrar objetivos, limitaciones y recomendaciones.

