import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Pet } from "../domain/types";
import { useAuth } from "./AuthContext";
import { api } from "./api";

interface PetContextValue {
  pets: Pet[];
  activePet: Pet | null;
  activePetId: string;
  setActivePetId: (id: string) => void;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
}

const PetContext = createContext<PetContextValue | null>(null);

export function PetProvider({ children }: PropsWithChildren): React.JSX.Element {
  const { user } = useAuth();
  const {
    data = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["pets", user?.id],
    queryFn: api.pets,
    enabled: Boolean(user),
    retry: false,
  });
  const [activePetId, setActivePetIdState] = useState(
    () => localStorage.getItem("hemovet4-active-pet") ?? "",
  );

  useEffect(() => {
    if (!activePetId && data[0]) setActivePetIdState(data[0].id);
    if (activePetId && data.length > 0 && !data.some((pet) => pet.id === activePetId)) {
      setActivePetIdState(data[0].id);
    }
  }, [activePetId, data]);

  const value = useMemo(
    () => ({
      pets: data,
      activePet: data.find((pet) => pet.id === activePetId) ?? data[0] ?? null,
      activePetId: activePetId || data[0]?.id || "",
      setActivePetId: (id: string) => {
        localStorage.setItem("hemovet4-active-pet", id);
        setActivePetIdState(id);
      },
      loading: isLoading,
      error,
      refetch,
    }),
    [activePetId, data, error, isLoading, refetch],
  );

  return <PetContext.Provider value={value}>{children}</PetContext.Provider>;
}

export function useActivePet(): PetContextValue {
  const context = useContext(PetContext);
  if (!context) throw new Error("useActivePet debe usarse dentro de PetProvider.");
  return context;
}
