import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { User } from "../domain/types";
import { useAuth } from "./AuthContext";
import { api } from "./api";

export type TourPlacement = "center" | "bottom" | "bottom-left" | "right";

export interface TourStep {
  id: string;
  route: string;
  target: string | null;
  title: string;
  description: string;
  placement: TourPlacement;
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    route: "/panel",
    target: null,
    title: "Bienvenido a HemoVet",
    description:
      "Este recorrido te muestra los módulos principales para interpretar, guardar y consultar hemogramas caninos con orientación responsable.",
    placement: "center",
  },
  {
    id: "panel-kpi",
    route: "/panel",
    target: '[data-tour="panel-kpi"]',
    title: "Panel de resumen",
    description:
      "Aquí revisas el estado general de la mascota activa, sus hemogramas guardados y el acceso rápido al siguiente análisis.",
    placement: "bottom",
  },
  {
    id: "analisis-upload",
    route: "/analisis/nuevo",
    target: '[data-tour="analisis-upload"]',
    title: "Cargar un hemograma",
    description:
      "Sube el archivo del laboratorio o ingresa los valores manualmente. Siempre podrás revisar los datos antes de enviarlos al modelo.",
    placement: "bottom",
  },
  {
    id: "mascotas-registrar",
    route: "/mascotas",
    target: '[data-tour="mascotas-registrar"]',
    title: "Registrar mascotas",
    description:
      "Crea el perfil de cada perro para guardar resultados, separar historiales y consultar su evolución de forma ordenada.",
    placement: "bottom",
  },
  {
    id: "vigilancia-mapa",
    route: "/vigilancia",
    target: '[data-tour="vigilancia-mapa"]',
    title: "Vigilancia comunitaria",
    description:
      "Consulta hallazgos agregados por zona. La información es anónima y no muestra direcciones ni ubicaciones exactas.",
    placement: "bottom",
  },
  {
    id: "asistente-chat",
    route: "/asistente",
    target: '[data-tour="asistente-composer"]',
    title: "Asistente con IA",
    description:
      "Escribe preguntas sobre términos o resultados. El asistente usa contexto autorizado y mantiene límites clínicos claros.",
    placement: "bottom",
  },
  {
    id: "biblioteca-buscar",
    route: "/biblioteca",
    target: '[data-tour="biblioteca-buscar"]',
    title: "Biblioteca clínica",
    description:
      "Busca términos como WBC, HCT o plaquetas para entenderlos en lenguaje sencillo antes de hablar con tu veterinario.",
    placement: "bottom",
  },
  {
    id: "done",
    route: "/panel",
    target: null,
    title: "¡Todo listo!",
    description:
      "Ya conoces el flujo principal. Puedes empezar registrando una mascota o cargando un hemograma para revisión.",
    placement: "center",
  },
];

export const TOUR_VERSION = "hemovet4-main-v1";
export const LEGACY_TOUR_KEY = "hemovet4-tour-done";

interface TourContextValue {
  active: boolean;
  stepIndex: number;
  totalSteps: number;
  currentStep: TourStep;
  start: () => void;
  next: () => void;
  prev: () => void;
  skip: () => void;
}

const TourContext = createContext<TourContextValue | null>(null);

export function shouldAutoStartTour(
  user: User | null,
  options: { currentVersion?: string; legacyCompleted?: boolean } = {},
): boolean {
  if (!user || user.role !== "user") return false;
  if (options.legacyCompleted) return false;
  const currentVersion = options.currentVersion ?? TOUR_VERSION;
  if (user.onboarding_tour_status === "pending") return true;
  return user.onboarding_tour_version !== currentVersion;
}

export function TourProvider({ children }: PropsWithChildren): React.JSX.Element {
  const { user, updateUser } = useAuth();
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [manualRun, setManualRun] = useState(false);

  // Ref keeps functions stable so they don't retrigger useEffects on callers
  const stepIndexRef = useRef(stepIndex);
  stepIndexRef.current = stepIndex;
  const manualRunRef = useRef(manualRun);
  manualRunRef.current = manualRun;
  const userRef = useRef(user);
  userRef.current = user;
  const updateUserRef = useRef(updateUser);
  updateUserRef.current = updateUser;
  const autoStartedForUserRef = useRef<string | null>(null);

  const begin = useCallback((options: { manual: boolean }) => {
    setManualRun(options.manual);
    stepIndexRef.current = 0;
    setStepIndex(0);
    setActive(true);
  }, []);

  const start = useCallback(() => begin({ manual: true }), [begin]);

  useEffect(() => {
    if (!user) {
      autoStartedForUserRef.current = null;
      setActive(false);
      return;
    }
    if (active || autoStartedForUserRef.current === user.id) return;

    const legacyCompleted = localStorage.getItem(LEGACY_TOUR_KEY) === "1";
    if (legacyCompleted) {
      autoStartedForUserRef.current = user.id;
      void api
        .updateOnboardingTour({ status: "skipped", version: TOUR_VERSION })
        .then((updatedUser) => {
          updateUserRef.current(updatedUser);
          localStorage.removeItem(LEGACY_TOUR_KEY);
        })
        .catch(() => undefined);
      return;
    }

    if (shouldAutoStartTour(user)) {
      autoStartedForUserRef.current = user.id;
      begin({ manual: false });
    }
  }, [active, begin, user]);

  const closeWithStatus = useCallback((status: "completed" | "skipped") => {
    const isManual = manualRunRef.current;
    setActive(false);
    setManualRun(false);
    if (isManual) return;

    const currentUser = userRef.current;
    if (!currentUser) {
      localStorage.setItem(LEGACY_TOUR_KEY, "1");
      return;
    }

    void api
      .updateOnboardingTour({ status, version: TOUR_VERSION })
      .then((updatedUser) => {
        updateUserRef.current(updatedUser);
        localStorage.removeItem(LEGACY_TOUR_KEY);
      })
      .catch(() => {
        localStorage.setItem(LEGACY_TOUR_KEY, "1");
      });
  }, []);

  const next = useCallback(() => {
    const current = stepIndexRef.current;
    if (current >= TOUR_STEPS.length - 1) {
      closeWithStatus("completed");
    } else {
      const nextIndex = current + 1;
      stepIndexRef.current = nextIndex;
      setStepIndex(nextIndex);
    }
  }, [closeWithStatus]);

  const prev = useCallback(() => {
    const current = stepIndexRef.current;
    if (current > 0) {
      const nextIndex = current - 1;
      stepIndexRef.current = nextIndex;
      setStepIndex(nextIndex);
    }
  }, []);

  const skip = useCallback(() => {
    closeWithStatus("skipped");
  }, [closeWithStatus]);

  const value = useMemo<TourContextValue>(
    () => ({
      active,
      stepIndex,
      totalSteps: TOUR_STEPS.length,
      currentStep: TOUR_STEPS[stepIndex],
      start,
      next,
      prev,
      skip,
    }),
    [active, stepIndex, start, next, prev, skip],
  );

  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}

export function useTour(): TourContextValue {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error("useTour debe usarse dentro de TourProvider.");
  return ctx;
}
