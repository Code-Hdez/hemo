import { Laptop, Moon, Sun } from "lucide-react";
import { Button } from "react-aria-components";
import { useTheme } from "../app/ThemeContext";
import type { ThemePreference } from "../domain/types";

const options: Array<{ value: ThemePreference; label: string; icon: typeof Sun }> = [
  { value: "light", label: "Claro", icon: Sun },
  { value: "system", label: "Sistema", icon: Laptop },
  { value: "dark", label: "Oscuro", icon: Moon },
];

export function ThemeToggle({ compact = false }: { compact?: boolean }): React.JSX.Element {
  const { preference, setPreference } = useTheme();
  return (
    <fieldset className={compact ? "theme-toggle theme-toggle--compact" : "theme-toggle"}>
      <legend className="sr-only">Tema visual</legend>
      {options.map((option) => (
        <Button
          key={option.value}
          className="theme-toggle__button"
          data-active={preference === option.value}
          onPress={() => setPreference(option.value)}
          aria-label={`Usar tema ${option.label.toLowerCase()}`}
        >
          <option.icon size={16} aria-hidden="true" />
          {!compact && <span>{option.label}</span>}
        </Button>
      ))}
    </fieldset>
  );
}
