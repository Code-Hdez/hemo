import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ThemePreference } from "../domain/types";

interface ThemeContextValue {
  preference: ThemePreference;
  resolved: "light" | "dark";
  setPreference: (preference: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function resolveTheme(preference: ThemePreference): "light" | "dark" {
  if (preference !== "system") return preference;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: PropsWithChildren): React.JSX.Element {
  const [preference, setPreferenceState] = useState<ThemePreference>(
    () => (localStorage.getItem("hemovet4-theme") as ThemePreference | null) ?? "system",
  );
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolveTheme(preference));

  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const next = resolveTheme(preference);
      setResolved(next);
      document.documentElement.dataset.theme = next;
      document.documentElement.dataset.themePreference = preference;
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute("content", next === "dark" ? "#111719" : "#f4f7f8");
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [preference]);

  const value = useMemo(
    () => ({
      preference,
      resolved,
      setPreference: (next: ThemePreference) => {
        localStorage.setItem("hemovet4-theme", next);
        setPreferenceState(next);
      },
    }),
    [preference, resolved],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme debe usarse dentro de ThemeProvider.");
  return context;
}
