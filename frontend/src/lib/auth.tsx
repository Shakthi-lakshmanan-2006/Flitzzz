import React, { createContext, useContext, useEffect, useState } from "react";
import { type GoogleUserProfile } from "./google-auth";

export type User = {
  name: string;
  email: string;
  picture?: string | undefined;
  googleId?: string | undefined;
  role?: string | undefined;
  token?: string | undefined;
  authProvider?: "google" | "credentials" | undefined;
};

type AuthContextType = {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (email: string, pass: string) => Promise<boolean>;
  loginWithGoogle: (profile: GoogleUserProfile) => Promise<boolean>;
  signup: (name: string, email: string, pass: string) => Promise<boolean>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_STORAGE_KEY = "flitzz_auth_user";
const TOKEN_STORAGE_KEY = "flitzz_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  });

  const isAuthenticated = !!user;

  useEffect(() => {
    if (user) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }

    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }, [user, token]);

  const login = async (email: string, pass: string): Promise<boolean> => {
    try {
      const response = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.includes("@") ? email : `${email}@flitzz.ai`,
          password: pass,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const loggedUser: User = {
          name: data.user?.name || email,
          email: data.user?.email || email,
          role: data.user?.role || "Flight Manager & Dispatcher",
          token: data.token,
          authProvider: "credentials",
        };
        setUser(loggedUser);
        setToken(data.token);
        return true;
      }
    } catch {
      // Fallback mode if FastAPI backend is not active
    }

    await new Promise((res) => setTimeout(res, 300));
    const fallbackUser: User = {
      name: email.includes("@")
        ? email.split("@")[0]!.replace(".", " ").replace("_", " ")
        : email || "Flight Captain",
      email: email.includes("@") ? email : `${email}@flitzz.ai`,
      role: "Flight Manager & Dispatcher",
      token: `flitzz_token_${Date.now()}`,
      authProvider: "credentials",
    };
    setUser(fallbackUser);
    setToken(fallbackUser.token!);
    return true;
  };

  /**
   * Google Sign-In Handler
   * Currently authenticates frontend session and stores profile.
   * Prepared for future FastAPI integration via POST /api/auth/google.
   */
  const loginWithGoogle = async (profile: GoogleUserProfile): Promise<boolean> => {
    /*
     * FUTURE FASTAPI INTEGRATION PREPARATION:
     * When FastAPI backend is ready, replace below with:
     *
     * const response = await fetch("http://localhost:8000/api/auth/google", {
     *   method: "POST",
     *   headers: { "Content-Type": "application/json" },
     *   body: JSON.stringify({ credential: profile.credentialToken })
     * });
     * const data = await response.json();
     * setUser(data.user);
     * setToken(data.token);
     */

    const googleUser: User = {
      name: profile.name,
      email: profile.email,
      picture: profile.picture,
      googleId: profile.googleId,
      role: "Aviation Dispatcher & Captain",
      token: profile.credentialToken || `google_token_${Date.now()}`,
      authProvider: "google",
    };

    setUser(googleUser);
    setToken(googleUser.token!);
    return true;
  };

  const signup = async (name: string, email: string, pass: string): Promise<boolean> => {
    try {
      const response = await fetch("http://localhost:8000/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: name, email, password: pass }),
      });

      if (response.ok) {
        return true;
      }
    } catch {
      // Fallback
    }
    await new Promise((res) => setTimeout(res, 400));
    return true;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);

    // Revoke Google session if loaded
    try {
      const g = (
        window as unknown as {
          google?: { accounts?: { id?: { disableAutoSelect: () => void } } };
        }
      ).google;
      if (g?.accounts?.id) {
        g.accounts.id.disableAutoSelect();
      }
    } catch {
      // Ignore
    }
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, user, token, login, loginWithGoogle, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
