# HemoVet Frontend 4

Dashboard ciudadano principal de HemoVet, construido con React 19.2.1. Consume la API FastAPI real mediante `/api/v1`; MSW solo se
activa explícitamente para pruebas o demostraciones locales.

## Alcance

- Acceso mediante registro, login JWT y restauración de sesión.
- Dashboard por mascota con último resultado, historial y acciones directas reales.
- Flujo PDF -> extracción -> revisión humana -> análisis ML del backend.
- Registro de mascotas con consentimiento de zona epidemiológica agregada.
- Mapa comunitario, búsqueda voluntaria de atención veterinaria cercana desde
  la zona protegida, historial gráfico, biblioteca y asistente con fuentes.
- Panel técnico exclusivo para el rol administrador.
- Temas claro, oscuro y sistema en todas las vistas.
- Avisos clínicos persistentes: HemoVet no diagnostica ni sustituye el juicio veterinario.

## Desarrollo

```bash
nvm use
npm ci
npm run dev
```

El contrato del repositorio es Node.js 22, declarado en `.nvmrc` y utilizado
por CI.

La aplicación queda disponible en `http://localhost:5175`.

Acceso propietario:

```text
propietario@hemovet.demo
Demo1234
```

Acceso administrador:

```text
admin@hemovet.demo
Demo1234
```

## Verificación

```bash
npm run check
npm test
npm run build
npm run test:e2e
```

## Arquitectura

- React, TypeScript y Vite.
- TanStack Router y TanStack Query.
- React Aria Components para controles accesibles.
- React Hook Form y Zod para formularios.
- MSW opcional para contratos HTTP de prueba.
- Chart.js y MapLibre cargados únicamente en sus rutas.
- Vitest, Playwright y axe-core para pruebas.

Para ejecutar los fixtures de MSW, inicia Vite con `VITE_ENABLE_MSW=true`. En desarrollo normal,
Vite hace proxy de `/api` a `http://127.0.0.1:8000`; el contenedor Nginx hace el mismo proxy al
servicio `backend`.
