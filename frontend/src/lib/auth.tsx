"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiFetch, setAccessToken } from "./api";

interface OrgInfo {
  id: string;
  name: string;
  role: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  organizations: OrgInfo[];
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    password: string,
    fullName: string,
    orgName: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const saveTokens = (tokens: TokenResponse) => {
    setAccessToken(tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
  };

  const fetchUser = useCallback(async () => {
    try {
      const u = await apiFetch<User>("/auth/me");
      setUser(u);
    } catch {
      setAccessToken(null);
      localStorage.removeItem("refresh_token");
      setUser(null);
    }
  }, []);

  const tryRefresh = useCallback(async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      setLoading(false);
      return;
    }
    try {
      const tokens = await apiFetch<TokenResponse>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      saveTokens(tokens);
      await fetchUser();
    } catch {
      localStorage.removeItem("refresh_token");
    } finally {
      setLoading(false);
    }
  }, [fetchUser]);

  useEffect(() => {
    tryRefresh();
  }, [tryRefresh]);

  const login = async (email: string, password: string) => {
    const tokens = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveTokens(tokens);
    await fetchUser();
  };

  const signup = async (
    email: string,
    password: string,
    fullName: string,
    orgName: string
  ) => {
    const tokens = await apiFetch<TokenResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        org_name: orgName,
      }),
    });
    saveTokens(tokens);
    await fetchUser();
  };

  const logout = () => {
    setAccessToken(null);
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
