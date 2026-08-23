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
      // Three HRs work the same pool at once, so a stale screen is a real
      // hazard: two people claiming the same applicant, or an HR recording a
      // payment against a balance someone else already changed.
      staleTime: 15_000,
      refetchInterval: 30_000,
      // Polling pauses while the tab is hidden — no point spending requests
      // on a screen nobody is looking at. Refetching on focus covers the
      // return, so coming back to the tab shows current figures immediately.
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: true,
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
