import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import App from "@/App";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { ApiError } from "@/lib/api";
import "@/styles/globals.css";
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Auth failures are terminal — retrying them just delays the redirect.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.isAuthError) && failureCount < 2,
    },
  },
});
const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("Root element #root not found");
createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster position="top-right" richColors closeButton />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
