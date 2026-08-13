import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { User } from "../domain/types";
import { api, setUnauthorizedHandler } from "./api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren): React.JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const activeToken = localStorage.getItem("hemovet4-token");
    if (import.meta.env.VITE_ENABLE_MSW === "true" && !activeToken) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => {
        if (activeToken) localStorage.removeItem("hemovet4-token");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        const token = await api.login(email, password);
        if (import.meta.env.VITE_ENABLE_MSW === "true") {
          localStorage.setItem("hemovet4-token", token.access_token);
        } else {
          localStorage.removeItem("hemovet4-token");
        }
        const current = await api.me();
        setUser(current);
        return current;
      },
      logout: async () => {
        await api.logout().catch(() => undefined);
        localStorage.removeItem("hemovet4-token");
        localStorage.removeItem("hemovet4-active-pet");
        setUser(null);
      },
      updateUser: (nextUser) => setUser(nextUser),
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider.");
  return context;
}
