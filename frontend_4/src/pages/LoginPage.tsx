import { Link } from "@tanstack/react-router";
import { Eye, EyeOff, HeartPulse, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../app/AuthContext";
import { GuestModeModal } from "../components/GuestModeModal";
import { ThemeToggle } from "../components/ThemeToggle";

function RequiredMark(): React.JSX.Element {
  return (
    <span className="required-mark" aria-hidden="true">
      {" "}
      (*)
    </span>
  );
}

export function LoginPage(): React.JSX.Element {
  const { login, logout } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [guestModalOpen, setGuestModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login(email.trim(), password);
      window.location.assign(user.role === "admin" ? "/panel-tecnico" : "/panel");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible iniciar sesión.");
    } finally {
      setSubmitting(false);
    }
  }

  async function enterGuestMode(): Promise<void> {
    setError("");
    setGuestModalOpen(false);
    await logout();
    localStorage.removeItem("hemovet4-token");
    localStorage.removeItem("hemovet4-active-pet");
    window.location.assign("/panel");
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-panel__top">
          <Link className="brand brand--auth" to="/" aria-label="HemoVet">
            <span className="brand__mark" aria-hidden="true">
              H
            </span>
            <span className="brand__copy">
              <strong>HemoVet</strong>
              <small>Orientación hematológica canina</small>
            </span>
          </Link>
          <ThemeToggle compact />
        </div>

        <div className="auth-panel__body">
          <p className="eyebrow">Acceso al dashboard</p>
          <h1 id="login-title">Revisa la información de tu mascota</h1>
          <p className="auth-panel__lead">
            Entra para consultar hemogramas guardados, registrar mascotas y usar el asistente con
            contexto.
          </p>

          <form className="auth-form" onSubmit={submit}>
            <label>
              <span>
                Correo electrónico
                <RequiredMark />
              </span>
              <div className="input-with-icon">
                <Mail size={18} aria-hidden="true" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (error) setError("");
                  }}
                  autoComplete="email"
                  required
                />
              </div>
            </label>
            <label>
              <span>
                Contraseña
                <RequiredMark />
              </span>
              <div className="input-with-icon">
                <LockKeyhole size={18} aria-hidden="true" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    if (error) setError("");
                  }}
                  autoComplete="current-password"
                  required
                />
                <button
                  className="input-icon-button"
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
            {error && (
              <div className="form-error" role="alert">
                {error}
              </div>
            )}
            <button
              className="button button--primary button--full"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Ingresando..." : "Iniciar sesión"}
            </button>
          </form>

          <div className="guest-access">
            <button
              className="button button--secondary button--full"
              type="button"
              onClick={() => setGuestModalOpen(true)}
            >
              Entrar en modo invitado
            </button>
          </div>

          <p className="auth-register">
            ¿No tienes cuenta? <Link to="/registro">Crear una cuenta</Link>
          </p>
        </div>
      </section>

      <aside className="auth-context" aria-label="Propósito y límites de HemoVet">
        <div className="auth-context__content">
          <HeartPulse size={28} aria-hidden="true" />
          <p className="eyebrow">Plataforma ciudadana</p>
          <h2>Convierte un hemograma canino en información más comprensible.</h2>
          <ul>
            <li>Revisa los valores extraídos antes del análisis.</li>
            <li>Consulta hallazgos en lenguaje no técnico.</li>
            <li>Prepara preguntas para conversar con tu veterinario.</li>
          </ul>
          <div className="auth-safety">
            <ShieldCheck size={20} aria-hidden="true" />
            <p>
              HemoVet no diagnostica enfermedades, no indica tratamientos ni sustituye la evaluación
              veterinaria.
            </p>
          </div>
        </div>
      </aside>
      <GuestModeModal
        open={guestModalOpen}
        onClose={() => setGuestModalOpen(false)}
        onConfirm={() => void enterGuestMode()}
      />
    </main>
  );
}
