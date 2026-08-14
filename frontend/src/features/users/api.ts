import type { User, UserRole } from "@/features/auth/types";
import { api } from "@/lib/api";

export interface CreateUserInput {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  phone?: string | null;
}

export interface UpdateUserInput {
  full_name?: string;
  role?: UserRole;
  phone?: string | null;
  is_active?: boolean;
}

export interface PasswordReset {
  user_id: string;
  temporary_password: string;
}

export const usersApi = {
  list: () => api.get<User[]>("/admin/users"),
  create: (data: CreateUserInput) => api.post<User>("/admin/users", data),
  update: (id: string, data: UpdateUserInput) => api.patch<User>(`/admin/users/${id}`, data),
  resetPassword: (id: string) => api.post<PasswordReset>(`/admin/users/${id}/reset-password`),
  delete: (id: string) => api.del<void>(`/admin/users/${id}`),
};
