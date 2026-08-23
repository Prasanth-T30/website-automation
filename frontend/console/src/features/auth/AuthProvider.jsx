import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, use } from "react";
import { ApiError } from "@/lib/api";
import { authApi } from "./api";
const AuthContext = createContext(null);
export const SESSION_KEY = ["auth", "session"];
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: SESSION_KEY,
    queryFn: authApi.me,
    // A 401 here simply means "signed out" — it is an answer, not a failure.
    retry: false,
    staleTime: 5 * 60_000,
  });
  const loginMutation = useMutation({
    mutationFn: ({ email, password }) => authApi.login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(SESSION_KEY, data.user);
    },
  });
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    // Clear local state even if the network call failed — the user asked to
    // leave, and the cookies are gone or about to expire either way.
    onSettled: () => {
      queryClient.setQueryData(SESSION_KEY, null);
      queryClient.clear();
    },
  });
  const isUnauthenticated =
    session.isError && session.error instanceof ApiError && session.error.isAuthError;
  const user = session.data ?? null;
  const value = {
    user,
    isLoading: session.isPending && !isUnauthenticated,
    isAuthenticated: user !== null,
    isAdmin: user?.role === "admin",
    login: async (email, password) => {
      const data = await loginMutation.mutateAsync({ email, password });
      return data.user;
    },
    logout: async () => {
      await logoutMutation.mutateAsync();
    },
  };
  return <AuthContext value={value}>{children}</AuthContext>;
}
export function useAuth() {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
