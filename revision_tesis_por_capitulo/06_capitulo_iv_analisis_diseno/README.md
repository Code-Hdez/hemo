# 06 - Capitulo IV - Analisis y diseno

## Problema actual

El capitulo describe una arquitectura mas simple que la actual. Debe reflejar la arquitectura modular real.

## Cambios necesarios

### Analisis

Actualizar casos de uso:

- Registro e inicio de sesion.
- Gestion de mascotas.
- Carga de hemograma.
- Revision de extraccion.
- Analisis hematologico.
- Consulta al asistente.
- Consulta de historial por mascota.
- Vigilancia comunitaria agregada.
- Consulta de biblioteca/glosario.
- Acceso tecnico/admin a metricas.

### Diseno

Agregar o actualizar diagramas:

- Diagrama de componentes backend.
- Diagrama de flujo de analisis.
- Modelo de datos: usuarios, mascotas, analisis, mensajes de chat, eventos de vigilancia.
- Diagrama de despliegue: frontend, backend, PostgreSQL, ChromaDB, Ollama, Caddy/Nginx.
- Contrato API versionado `/api/v1`.

## Evidencia incluida

- `architecture.md`
- `llm-rag.md`
- `README.md`

## Nota

El documento debe evitar decir que el sistema depende solo de tres servicios simples. El sistema actual tiene mas dominios, aunque el despliegue siga siendo orquestado por Docker Compose.



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**Estado:** completo (4.1–4.3, P973–P1241), alineado con la arquitectura actual.
**Pendiente menor:** sin correcciones de fondo; verificar que los contratos API descritos coincidan con `/api/v1` actual.
