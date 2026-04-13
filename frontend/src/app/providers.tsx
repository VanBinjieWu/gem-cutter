import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { RuntimeSettingsProvider } from "./runtime";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 15_000,
    },
  },
});

export function Providers({ children }: { children: ReactNode }) {
  return (
    <RuntimeSettingsProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </RuntimeSettingsProvider>
  );
}

