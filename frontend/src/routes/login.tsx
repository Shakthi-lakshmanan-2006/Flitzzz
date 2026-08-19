import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User as UserIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Logo } from "@/components/flitz-ui";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth";
import { promptGoogleOAuth } from "@/lib/google-auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function verifyGoogleWithBackend(googleResult: any) {
  const credential =
    googleResult?.credential ??
    googleResult?.id_token ??
    googleResult?.idToken;

  // If the existing OAuth helper already returns a verified application
  // profile, preserve the existing flow.
  if (!credential) {
    return googleResult;
  }

  const response = await fetch(`${API_BASE_URL}/auth/google`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ credential }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Google authentication failed.");
  }

  return data;
}

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Welcome to Flitzz — Login" },
      {
        name: "description",
        content: "Sign in to your Flitzz aviation delay prediction & operational workspace.",
      },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login, loginWithGoogle } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [forgotSent, setForgotSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // If already authenticated, redirect to /home
  useEffect(() => {
    if (isAuthenticated) {
      navigate({ to: "/home" });
    }
  }, [isAuthenticated, navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username || "captain.pilot@flitzz.ai", password);
      navigate({ to: "/home" });
    } catch {
      setError("Invalid credentials. Please verify your login details.");
      setBusy(false);
    }
  }

  async function handleGoogleLogin() {
    setError("");
    setBusy(true);
    try {
      await promptGoogleOAuth(
        async (googleProfile) => {
          const verifiedGoogle = await verifyGoogleWithBackend(googleProfile);
          await loginWithGoogle(
            verifiedGoogle?.google ?? verifiedGoogle ?? googleProfile,
          );
          navigate({ to: "/home" });
        },
        (errorMsg) => {
          setError(errorMsg || "Google Sign-In was cancelled or failed.");
          setBusy(false);
        },
      );
    } catch {
      setError("Google authentication process failed. Please try again.");
      setBusy(false);
    }
  }

  function handleForgotPassword() {
    setForgotSent(true);
    setTimeout(() => setForgotSent(false), 5000);
  }

  return (
    <div className="min-h-screen bg-background grid lg:grid-cols-2 overflow-hidden">
      {/* ==========================================
          LEFT SIDE (~50% width on desktop):
          FULL-HEIGHT IMAGE WITH CREATIVE ORGANIC MASK
          ========================================== */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden bg-card/40">
        {/* Organic Wave / Curved Mask Image Container */}
        <div
          className="absolute inset-0 bg-cover bg-center opacity-90 transition-transform duration-700 hover:scale-105"
          style={{
            backgroundImage: "url('/login-wing.jpg')",
            clipPath: "polygon(0 0, 100% 0, 86% 35%, 98% 70%, 88% 100%, 0% 100%)",
          }}
          aria-hidden
        />

        {/* Dark Tint Overlay matching mask */}
        <div
          className="absolute inset-0 bg-gradient-to-t from-background/95 via-background/40 to-background/20"
          style={{
            clipPath: "polygon(0 0, 100% 0, 86% 35%, 98% 70%, 88% 100%, 0% 100%)",
          }}
          aria-hidden
        />

        {/* Top Header Logo */}
        <div className="relative z-10">
          <Logo />
        </div>
      </div>

      {/* ==========================================
          RIGHT SIDE (~50% width on desktop):
          LOGIN FUNCTIONALITY & CONTENT STRUCTURE
          ========================================== */}
      <div className="flex flex-col p-8 sm:p-12 justify-between">
        <div className="flex items-center justify-between">
          <div className="lg:hidden">
            <Logo />
          </div>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>

        <div className="my-auto py-8">
          <div className="w-full max-w-sm mx-auto">
            {/* 1. WELCOME MESSAGE */}
            <div className="mb-2">
              <span className="text-xs font-extrabold uppercase tracking-[0.2em] text-primary">
                Aviation Dispatch Portal
              </span>
              <h1 className="mt-1 text-3xl font-black tracking-tight sm:text-4xl text-foreground">
                Welcome to Flitzz
              </h1>
              <p className="mt-2 text-xs text-muted-foreground">
                Sign in with your organizational account to monitor flight delay risks and dispatch
                recovery.
              </p>
            </div>

            {error && (
              <div className="mt-4 rounded-xl border border-destructive/50 bg-destructive/10 p-3 text-xs text-destructive">
                {error}
              </div>
            )}

            {forgotSent && (
              <div className="mt-4 rounded-xl border border-emerald-500/50 bg-emerald-500/10 p-3 text-xs text-emerald-400">
                Password reset link has been dispatched to your registered email address.
              </div>
            )}

            {/* 2. TRADITIONAL LOGIN FORM (INPUT DETAILS) */}
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {/* Name / Username / Email Field */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Name or Work Email *
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Captain John Doe or ops@airline.com"
                    className="w-full rounded-xl border border-input bg-background/70 py-2.5 pl-10 pr-3 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
                  />
                </div>
              </div>

              {/* Password Field with Masking Visibility Toggle */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Password *
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-input bg-background/70 py-2.5 pl-10 pr-10 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* REMEMBER ME & FORGOT PASSWORD */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 rounded accent-primary cursor-pointer"
                  />
                  <span className="text-muted-foreground font-medium">Remember me</span>
                </label>

                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="font-semibold text-primary hover:underline"
                >
                  Forgot Password?
                </button>
              </div>

              {/* PRIMARY LOGIN BUTTON */}
              <button
                type="submit"
                disabled={busy}
                className="bg-brand mt-2 w-full inline-flex items-center justify-center gap-2 rounded-full py-3.5 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02] disabled:opacity-70"
              >
                {busy ? "Logging in…" : "Login to Dashboard"} <ArrowRight className="h-4 w-4" />
              </button>
            </form>

            {/* DIVIDER */}
            <div className="relative my-6 text-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border/60" />
              </div>
              <span className="relative bg-background px-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Or Continue With
              </span>
            </div>

            {/* 3. SOCIAL LOGIN OPTION: CONTINUE WITH GOOGLE (BELOW DETAILS) */}
            <div>
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={busy}
                className="glass w-full inline-flex items-center justify-center gap-3 rounded-full py-3 px-4 text-xs font-bold transition-all hover:bg-accent hover:border-primary/50 hover:shadow-glow"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.15C3.26 21.3 7.31 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.61H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.39l3.99-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.61l3.99 3.15c.95-2.85 3.6-4.96 6.72-4.96z"
                  />
                </svg>
                Continue with Google
              </button>
            </div>

            <p className="mt-6 text-center text-xs text-muted-foreground">
              Don't have an account?{" "}
              <Link to="/signup" className="text-primary font-semibold hover:underline">
                Sign Up
              </Link>
            </p>
          </div>
        </div>

        <div className="text-xs text-muted-foreground text-center sm:text-left">
          &copy; {new Date().getFullYear()} Flitzz Aviation Intelligence Inc. All rights reserved.
        </div>
      </div>
    </div>
  );
}