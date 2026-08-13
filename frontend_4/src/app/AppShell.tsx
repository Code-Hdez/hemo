import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import {
  BarChart3,
  BookOpen,
  Bot,
  ChevronLeft,
  ClipboardPlus,
  LayoutDashboard,
  LogIn,
  LogOut,
  Map as MapIcon,
  Menu,
  PawPrint,
  Settings,
  ShieldAlert,
  X,
} from "lucide-react";
import { useState } from "react";
import { PetAvatar } from "../components/PetAvatar";
import { SafetyBar } from "../components/SafetyBar";
import { ThemeToggle } from "../components/ThemeToggle";
import { TourOverlay } from "../components/TourOverlay";
import { useAuth } from "./AuthContext";
import { useActivePet } from "./PetContext";

const mainNavigation = [
  { to: "/panel", label: "Resumen", icon: LayoutDashboard, tourId: "nav-resumen" },
  { to: "/analisis/nuevo", label: "Nuevo hemograma", icon: ClipboardPlus, tourId: "nav-analisis" },
  { to: "/mascotas", label: "Mascotas", icon: PawPrint, tourId: "nav-mascotas" },
  { to: "/vigilancia", label: "Vigilancia", icon: MapIcon, tourId: "nav-vigilancia" },
  { to: "/asistente", label: "Asistente", icon: Bot, tourId: "nav-asistente" },
  { to: "/biblioteca", label: "Biblioteca", icon: BookOpen, tourId: "nav-biblioteca" },
] as const;

function ShellContent(): React.JSX.Element {
  const { user, logout } = useAuth();
  const { pets, activePet, activePetId, setActivePetId } = useActivePet();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell" data-sidebar-collapsed={collapsed}>
      <a className="skip-link" href="#main-content">
        Saltar al contenido principal
      </a>
      <aside className="sidebar" data-mobile-open={mobileOpen}>
        <div className="sidebar__brand">
          <Link to="/panel" className="brand" aria-label="Ir al resumen de HemoVet">
            <span className="brand__mark" aria-hidden="true">
              H
            </span>
            <span className="brand__copy">
              <strong>HemoVet</strong>
              <small>Orientación canina</small>
            </span>
          </Link>
          <button
            className="icon-button sidebar__mobile-close"
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar navegación"
          >
            <X size={19} />
          </button>
        </div>

        <nav className="sidebar__nav" aria-label="Navegación principal">
          {mainNavigation.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="sidebar__link"
              activeProps={{ className: "sidebar__link sidebar__link--active" }}
              activeOptions={{ exact: item.to === "/panel" }}
              title={collapsed ? item.label : undefined}
              onClick={() => setMobileOpen(false)}
              data-tour={item.tourId}
            >
              <item.icon size={19} aria-hidden="true" />
              <span className="sidebar__label">{item.label}</span>
            </Link>
          ))}
          {user?.role === "admin" && (
            <Link
              to="/panel-tecnico"
              className="sidebar__link"
              activeProps={{ className: "sidebar__link sidebar__link--active" }}
              title={collapsed ? "Panel técnico" : undefined}
              onClick={() => setMobileOpen(false)}
            >
              <BarChart3 size={19} aria-hidden="true" />
              <span className="sidebar__label">Panel técnico</span>
            </Link>
          )}
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__theme">
            <ThemeToggle compact />
          </div>
          <Link
            to="/limites"
            className="sidebar__link"
            activeProps={{ className: "sidebar__link sidebar__link--active" }}
            title={collapsed ? "Límites del sistema" : undefined}
            data-tour="nav-limites"
          >
            <ShieldAlert size={19} aria-hidden="true" />
            <span className="sidebar__label">Límites del sistema</span>
          </Link>
          <button
            className="sidebar__link"
            type="button"
            onClick={() => {
              if (!user) {
                window.location.href = "/login";
                return;
              }
              void logout().then(() => {
                window.location.href = "/login";
              });
            }}
            title={collapsed ? (user ? "Cerrar sesión" : "Iniciar sesión") : undefined}
          >
            {user ? (
              <LogOut size={19} aria-hidden="true" />
            ) : (
              <LogIn size={19} aria-hidden="true" />
            )}
            <span className="sidebar__label">{user ? "Cerrar sesión" : "Iniciar sesión"}</span>
          </button>
          <button
            className="sidebar__collapse"
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "Expandir navegación" : "Contraer navegación"}
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button topbar__menu"
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir navegación"
          >
            <Menu size={20} />
          </button>
          <div className="topbar__context">
            <span className="topbar__route">
              {mainNavigation.find((item) => pathname.startsWith(item.to))?.label ?? "HemoVet"}
            </span>
            {activePet && (
              <label className="pet-select" data-tour="pet-selector">
                <span className="sr-only">Mascota activa</span>
                <PetAvatar pet={activePet} size="small" />
                <select
                  value={activePetId}
                  onChange={(event) => setActivePetId(event.target.value)}
                >
                  {pets.map((pet) => (
                    <option key={pet.id} value={pet.id}>
                      {pet.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="topbar__actions">
            <ThemeToggle compact />
            <Link
              to={user ? "/cuenta" : "/login"}
              className="account-button"
              aria-label={user ? "Abrir configuración de cuenta" : "Iniciar sesión"}
              data-tour="account-button"
            >
              <span>{user?.full_name?.slice(0, 1) ?? "I"}</span>
              <div>
                <strong>{user?.full_name ?? "Modo invitado"}</strong>
                <small>
                  {user ? (user.role === "admin" ? "Administrador" : "Propietario") : "Temporal"}
                </small>
              </div>
              <Settings size={17} aria-hidden="true" />
            </Link>
          </div>
        </header>

        <SafetyBar />
        <main id="main-content" className="main-content">
          <Outlet />
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Navegación móvil">
        {mainNavigation.slice(0, 4).map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="mobile-nav__link"
            activeProps={{ className: "mobile-nav__link mobile-nav__link--active" }}
          >
            <item.icon size={19} aria-hidden="true" />
            <span>{item.label === "Nuevo hemograma" ? "Analizar" : item.label}</span>
          </Link>
        ))}
        <button className="mobile-nav__link" type="button" onClick={() => setMobileOpen(true)}>
          <Menu size={19} aria-hidden="true" />
          <span>Más</span>
        </button>
      </nav>

      <TourOverlay />
    </div>
  );
}

export function AppShell(): React.JSX.Element {
  return <ShellContent />;
}
