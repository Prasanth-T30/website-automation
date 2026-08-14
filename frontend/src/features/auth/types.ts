export type UserRole = "admin" | "hr";

export interface User {
  /** Firestore document ID — an opaque string, not a numeric primary key. */
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  phone: string | null;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface SessionResponse {
  user: User;
}
