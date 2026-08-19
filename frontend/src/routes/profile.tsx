import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { CheckCircle2, Key, LogOut, Mail, Shield, User as UserIcon } from "lucide-react";
import { useEffect } from "react";

import { GlassCard, PageShell } from "@/components/flitz-ui";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "User Profile — Flitzz" },
      {
        name: "description",
        content: "View and manage your Flitzz user account profile and dispatcher credentials.",
      },
    ],
  }),
  component: ProfilePage,
});

function ProfilePage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  // Protection: Redirect unauthenticated users to /login
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated || !user) return null;

  return (
    <PageShell
      eyebrow="Protected Route • User Account"
      title="User Profile & Credentials"
      description="Manage your Flight Dispatcher identity, active authorization session, and security settings."
    >
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Column: User Identity Card */}
        <GlassCard className="p-8 border-primary/30 text-center lg:col-span-1">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-brand text-primary-foreground shadow-glow mb-4 overflow-hidden relative">
            {user.picture ? (
              <img src={user.picture} alt={user.name} className="h-full w-full object-cover" />
            ) : (
              <UserIcon className="h-10 w-10" />
            )}
          </div>

          <h2 className="text-2xl font-extrabold text-foreground">{user.name}</h2>
          <p className="text-xs font-semibold text-primary mt-1">
            {user.role || "Flight Dispatcher & Manager"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{user.email}</p>

          {user.authProvider === "google" && (
            <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-accent/60 px-3 py-1 text-[11px] font-bold text-foreground border border-border">
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24">
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
              <span>Authenticated via Google OAuth</span>
            </div>
          )}

          <div className="mt-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 p-3.5 text-center">
            <span className="flex items-center justify-center gap-1.5 text-xs font-bold text-emerald-500">
              <CheckCircle2 className="h-4 w-4" /> Active Authenticated Session
            </span>
          </div>

          <div className="mt-8 border-t border-border/40 pt-6 space-y-3">
            <button
              onClick={() => {
                logout();
                navigate({ to: "/login" });
              }}
              className="bg-destructive/10 border border-destructive/30 text-destructive hover:bg-destructive/20 w-full inline-flex items-center justify-center gap-2 rounded-full py-3 text-xs font-bold transition-all"
            >
              <LogOut className="h-4 w-4" /> Logout of Session
            </button>
          </div>
        </GlassCard>

        {/* Right Column: Account Details & Permissions */}
        <GlassCard className="p-8 lg:col-span-2 space-y-6">
          <div>
            <h3 className="text-lg font-bold text-foreground">Account Information</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verified operational details and organizational authorization.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-border/60 bg-background/50 p-4">
              <span className="text-xs font-semibold text-muted-foreground">
                Dispatcher License ID
              </span>
              <p className="mt-1 text-sm font-bold text-foreground">FAA-DISP-984214</p>
            </div>
            <div className="rounded-2xl border border-border/60 bg-background/50 p-4">
              <span className="text-xs font-semibold text-muted-foreground">
                Carrier Organization
              </span>
              <p className="mt-1 text-sm font-bold text-foreground">Global Airways Operations</p>
            </div>
            <div className="rounded-2xl border border-border/60 bg-background/50 p-4">
              <span className="text-xs font-semibold text-muted-foreground">Account Created</span>
              <p className="mt-1 text-sm font-bold text-foreground">August 2026</p>
            </div>
            <div className="rounded-2xl border border-border/60 bg-background/50 p-4">
              <span className="text-xs font-semibold text-muted-foreground">ML API Key Access</span>
              <p className="mt-1 text-sm font-bold text-emerald-500">Tier 1 LightGBM + SHAP</p>
            </div>
          </div>

          <div className="border-t border-border/40 pt-6">
            <h4 className="text-sm font-bold text-foreground">Active Operational Permissions</h4>
            <div className="mt-3 space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <span>Execute 1-Click Passenger Rebooking & Digital Boarding Pass Generation</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <span>Issue Complimentary $45 Executive Airport Lounge Vouchers</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <span>Perform Standby Crew Roster Swaps & Fatigue Index Overrides</span>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>
    </PageShell>
  );
}
