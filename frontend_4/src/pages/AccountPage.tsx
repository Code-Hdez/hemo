import { BookOpen, LogOut, Mail, ShieldCheck, UserRound } from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { useTour } from "../app/TourContext";
import { PageHeader } from "../components/PageHeader";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { ThemeToggle } from "../components/ThemeToggle";

export function AccountPage(): React.JSX.Element {
  const { user, logout } = useAuth();
  const { start } = useTour();

  if (!user) {
    return (
      <PrivateFeatureGate description="La configuración de cuenta está disponible cuando inicias sesión. En modo invitado los análisis no se guardan." />
    );
  }

  return (
    <div className="account-page page-flow">
      <PageHeader
        eyebrow="Preferencias"
        title="Cuenta"
        description="Datos de sesión y apariencia del dashboard."
      />
      <div className="settings-layout">
        <section className="dashboard-panel settings-section">
          <div className="settings-section__heading">
            <span>
              <UserRound size={20} aria-hidden="true" />
            </span>
            <div>
              <h2>Perfil</h2>
              <p>Información de tu cuenta en HemoVet.</p>
            </div>
          </div>
          <dl className="settings-list">
            <div>
              <dt>Nombre</dt>
              <dd>{user?.full_name}</dd>
            </div>
            <div>
              <dt>
                <Mail size={16} aria-hidden="true" /> Correo
              </dt>
              <dd>{user?.email}</dd>
            </div>
            <div>
              <dt>Rol</dt>
              <dd>{user?.role === "admin" ? "Administrador técnico" : "Propietario"}</dd>
            </div>
          </dl>
        </section>

        <section className="dashboard-panel settings-section">
          <div className="settings-section__heading">
            <span>
              <ShieldCheck size={20} aria-hidden="true" />
            </span>
            <div>
              <h2>Apariencia</h2>
              <p>La preferencia se conserva en este navegador.</p>
            </div>
          </div>
          <ThemeToggle />
        </section>

        <section className="dashboard-panel settings-section">
          <div className="settings-section__heading">
            <span>
              <BookOpen size={20} aria-hidden="true" />
            </span>
            <div>
              <h2>Tutorial interactivo</h2>
              <p>Repasa el tour de bienvenida para conocer cada módulo del sistema.</p>
            </div>
          </div>
          <button className="button button--secondary" type="button" onClick={start}>
            Repetir tutorial
          </button>
        </section>

        <section className="dashboard-panel settings-section">
          <div className="settings-section__heading">
            <span>
              <LogOut size={20} aria-hidden="true" />
            </span>
            <div>
              <h2>Sesión</h2>
              <p>Cierra el acceso a los datos de esta sesión en este navegador.</p>
            </div>
          </div>
          <button
            className="button button--danger"
            type="button"
            onClick={() => {
              void logout().then(() => {
                window.location.href = "/";
              });
            }}
          >
            Cerrar sesión
          </button>
        </section>
      </div>
    </div>
  );
}
