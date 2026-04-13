import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

const API_BASE_STORAGE_KEY = "gem-cutter.apiBaseUrl";

export const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_GEM_CUTTER_API_BASE_URL || "http://127.0.0.1:8000";

interface RuntimeSettings {
  apiBaseUrl: string;
  setApiBaseUrl: (value: string) => void;
}

const RuntimeSettingsContext = createContext<RuntimeSettings | null>(null);

function readInitialApiBaseUrl() {
  if (typeof window === "undefined") {
    return DEFAULT_API_BASE_URL;
  }
  return window.localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE_URL;
}

export function RuntimeSettingsProvider({ children }: { children: ReactNode }) {
  const [apiBaseUrl, setApiBaseUrlState] = useState(readInitialApiBaseUrl);

  const setApiBaseUrl = (value: string) => {
    const nextValue = value.trim() || DEFAULT_API_BASE_URL;
    setApiBaseUrlState(nextValue);
    window.localStorage.setItem(API_BASE_STORAGE_KEY, nextValue);
  };

  return (
    <RuntimeSettingsContext.Provider value={{ apiBaseUrl, setApiBaseUrl }}>
      {children}
    </RuntimeSettingsContext.Provider>
  );
}

export function useRuntimeSettings() {
  const context = useContext(RuntimeSettingsContext);
  if (!context) {
    throw new Error("useRuntimeSettings must be used within RuntimeSettingsProvider");
  }
  return context;
}

