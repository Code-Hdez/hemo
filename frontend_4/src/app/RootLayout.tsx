import { Outlet, useRouterState } from "@tanstack/react-router";
import { LoadingState } from "../components/LoadingState";
import { AppShell } from "./AppShell";
import { useAuth } from "./AuthContext";

export function RootLayout(): React.JSX.Element {
  const { loading } = useAuth();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const publicRoute = pathname === "/" || pathname === "/login" || pathname === "/registro";

  if (loading) return <LoadingState label="Preparando tu espacio" />;
  if (publicRoute) return <Outlet />;
  return <AppShell />;
}
