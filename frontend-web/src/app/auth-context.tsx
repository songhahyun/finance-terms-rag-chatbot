import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { login as loginApi, signup as signupApi } from "@/lib/api";
import type { AuthUser, LoginRequest, SignupRequest, TokenResponse, UserRole } from "@/types/api";

interface AuthContextValue {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  signup: (payload: SignupRequest) => Promise<void>;
  logout: () => void;
}

const AUTH_STORAGE_KEY = "finance_rag_auth";

const AuthContext = createContext<AuthContextValue | null>(null);

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payloadBase64 = token.split(".")[1];
    if (!payloadBase64) return null;
    const normalized = payloadBase64.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function rolesFromPayload(payload: Record<string, unknown> | null): UserRole[] {
  const roles = payload?.roles;
  if (!Array.isArray(roles)) return ["user"];
  const normalized = roles.filter((role): role is UserRole => role === "admin" || role === "user");
  return normalized.length > 0 ? normalized : ["user"];
}

function userFromToken(token: string): AuthUser | null {
  const payload = parseJwtPayload(token);
  const username = payload?.sub;
  if (typeof username !== "string" || username.length === 0) return null;
  return { username, roles: rolesFromPayload(payload) };
}

function persistAuth(token: string | null): void {
  if (!token) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function AuthProvider({ children }: PropsWithChildren): JSX.Element {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  const applyToken = useCallback((nextToken: string | null) => {
    setToken(nextToken);
    persistAuth(nextToken);
    setUser(nextToken ? userFromToken(nextToken) : null);
  }, []);

  useEffect(() => {
    const savedToken = localStorage.getItem(AUTH_STORAGE_KEY);
    if (savedToken) {
      applyToken(savedToken);
    }
  }, [applyToken]);

  const handleAuthSuccess = useCallback(
    (response: TokenResponse) => {
      applyToken(response.access_token);
    },
    [applyToken],
  );

  const login = useCallback(
    async (payload: LoginRequest) => {
      const response = await loginApi(payload);
      handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const signup = useCallback(
    async (payload: SignupRequest) => {
      const response = await signupApi(payload);
      handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const logout = useCallback(() => {
    applyToken(null);
  }, [applyToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      login,
      signup,
      logout,
    }),
    [token, user, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
