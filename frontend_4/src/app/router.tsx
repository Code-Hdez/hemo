import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
} from "@tanstack/react-router";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { RegisterPage } from "../pages/RegisterPage";
import { RootLayout } from "./RootLayout";

const rootRoute = createRootRoute({ component: RootLayout, notFoundComponent: NotFoundPage });

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: LoginPage,
});

const loginAliasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
});

const registerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/registro",
  component: RegisterPage,
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/panel",
  component: lazyRouteComponent(() => import("../pages/DashboardPage"), "DashboardPage"),
});

const analysisRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/nuevo",
  component: lazyRouteComponent(() => import("../pages/AnalysisPage"), "AnalysisPage"),
});

const resultRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/$analysisId",
  component: lazyRouteComponent(() => import("../pages/AnalysisResultPage"), "AnalysisResultPage"),
});

const petsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mascotas",
  component: lazyRouteComponent(() => import("../pages/PetsPage"), "PetsPage"),
});

const petDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mascotas/$petId",
  component: lazyRouteComponent(() => import("../pages/PetDetailPage"), "PetDetailPage"),
});

const historyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mascotas/$petId/historial",
  component: lazyRouteComponent(() => import("../pages/HistoryPage"), "HistoryPage"),
});

const surveillanceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/vigilancia",
  component: lazyRouteComponent(() => import("../pages/SurveillancePage"), "SurveillancePage"),
});

const assistantRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/asistente",
  component: lazyRouteComponent(() => import("../pages/AssistantPage"), "AssistantPage"),
});

const libraryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/biblioteca",
  component: lazyRouteComponent(() => import("../pages/LibraryPage"), "LibraryPage"),
});

const definitionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/biblioteca/$slug",
  component: lazyRouteComponent(() => import("../pages/DefinitionPage"), "DefinitionPage"),
});

const accountRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/cuenta",
  component: lazyRouteComponent(() => import("../pages/AccountPage"), "AccountPage"),
});

const limitsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/limites",
  component: lazyRouteComponent(() => import("../pages/LimitsPage"), "LimitsPage"),
});

const technicalRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/panel-tecnico",
  component: lazyRouteComponent(() => import("../pages/TechnicalPage"), "TechnicalPage"),
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  loginAliasRoute,
  registerRoute,
  dashboardRoute,
  analysisRoute,
  resultRoute,
  petsRoute,
  petDetailRoute,
  historyRoute,
  surveillanceRoute,
  assistantRoute,
  libraryRoute,
  definitionRoute,
  accountRoute,
  limitsRoute,
  technicalRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
