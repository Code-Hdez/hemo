import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../app/api";
import { ThemeToggle } from "../components/ThemeToggle";
import { isValidProperName, normalizeSingleLineText } from "../domain/formValidation";

const schema = z
  .object({
    full_name: z
      .string()
      .transform(normalizeSingleLineText)
      .pipe(
        z
          .string()
          .min(2, "El nombre completo es obligatorio.")
          .refine(isValidProperName, "El nombre completo no puede contener números ni símbolos."),
      ),
    email: z.string().trim().pipe(z.email("Ingresa un correo electrónico válido.")),
    password: z
      .string()
      .min(8, "Usa al menos 8 caracteres.")
      .regex(/[A-Z]/, "Incluye una mayúscula.")
      .regex(/[0-9]/, "Incluye un número."),
    confirmation: z.string(),
  })
  .refine((data) => data.password === data.confirmation, {
    message: "Las contraseñas no coinciden.",
    path: ["confirmation"],
  });

type RegisterValues = z.infer<typeof schema>;

function RequiredMark(): React.JSX.Element {
  return (
    <span className="required-mark" aria-hidden="true">
      {" "}
      (*)
    </span>
  );
}

export function RegisterPage(): React.JSX.Element {
  const [success, setSuccess] = useState(false);
  const [serverError, setServerError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    reValidateMode: "onChange",
  });

  async function submit(values: RegisterValues): Promise<void> {
    setServerError("");
    try {
      await api.register({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
      });
      setSuccess(true);
    } catch (caught) {
      setServerError(caught instanceof Error ? caught.message : "No fue posible crear la cuenta.");
    }
  }

  return (
    <main className="auth-screen auth-screen--register">
      <section className="auth-panel">
        <div className="auth-panel__top">
          <a className="button button--ghost" href="/">
            <ArrowLeft size={17} aria-hidden="true" /> Volver
          </a>
          <ThemeToggle compact />
        </div>
        <div className="auth-panel__body">
          {success ? (
            <div className="success-state">
              <span>
                <Check size={24} aria-hidden="true" />
              </span>
              <h1>Cuenta creada</h1>
              <p>Tu cuenta se creó correctamente. Ya puedes iniciar sesión.</p>
              <a className="button button--primary" href="/">
                Ir a iniciar sesión
              </a>
            </div>
          ) : (
            <>
              <p className="eyebrow">Nueva cuenta</p>
              <h1>Crear acceso de propietario</h1>
              <p className="auth-panel__lead">
                La cuenta permite asociar cada hemograma con una mascota y conservar su historial.
              </p>
              <form className="auth-form" onSubmit={handleSubmit(submit)}>
                <label>
                  <span>
                    Nombre completo
                    <RequiredMark />
                  </span>
                  <input
                    {...register("full_name")}
                    autoComplete="name"
                    aria-invalid={Boolean(errors.full_name)}
                  />
                  {errors.full_name && (
                    <small className="field-error">{errors.full_name.message}</small>
                  )}
                </label>
                <label>
                  <span>
                    Correo electrónico
                    <RequiredMark />
                  </span>
                  <input
                    type="email"
                    {...register("email")}
                    autoComplete="email"
                    aria-invalid={Boolean(errors.email)}
                  />
                  {errors.email && <small className="field-error">{errors.email.message}</small>}
                </label>
                <label>
                  <span>
                    Contraseña
                    <RequiredMark />
                  </span>
                  <input
                    type="password"
                    {...register("password")}
                    autoComplete="new-password"
                    aria-invalid={Boolean(errors.password)}
                  />
                  {errors.password && (
                    <small className="field-error">{errors.password.message}</small>
                  )}
                </label>
                <label>
                  <span>
                    Confirmar contraseña
                    <RequiredMark />
                  </span>
                  <input
                    type="password"
                    {...register("confirmation")}
                    autoComplete="new-password"
                    aria-invalid={Boolean(errors.confirmation)}
                  />
                  {errors.confirmation && (
                    <small className="field-error">{errors.confirmation.message}</small>
                  )}
                </label>
                {serverError && (
                  <div className="form-error" role="alert">
                    {serverError}
                  </div>
                )}
                <button
                  className="button button--primary button--full"
                  type="submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Creando..." : "Crear cuenta"}
                </button>
              </form>
            </>
          )}
        </div>
      </section>
      <aside className="auth-context">
        <div className="auth-context__content">
          <ShieldCheck size={28} aria-hidden="true" />
          <p className="eyebrow">Privacidad</p>
          <h2>El mapa comunitario usa zonas agregadas, nunca la dirección exacta.</h2>
          <p>
            Al registrar una mascota se solicita una zona aproximada para contribuir, con
            consentimiento, a señales comunitarias anónimas.
          </p>
        </div>
      </aside>
    </main>
  );
}
