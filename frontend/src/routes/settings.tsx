import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Bell, CheckCircle2, Cpu, Key, Moon, Save, Shield, Smartphone } from "lucide-react";
import { useEffect, useState } from "react";

import { GlassCard, PageShell } from "@/components/flitz-ui";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Flitzz" },
      {
        name: "description",
        content: "Configure Flitzz application settings, notification triggers, and API keys.",
      },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [saved, setSaved] = useState(false);

  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(true);
  const [highRiskThreshold, setHighRiskThreshold] = useState("75");
  const [autoRebookEnabled, setAutoRebookEnabled] = useState(true);

  // Protection: Redirect unauthenticated users to /login
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) return null;

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <PageShell
      eyebrow="Protected Route • Configuration"
      title="Application & Account Settings"
      description="Customize prediction alert sensitivity, automated passenger rebooking triggers, and API configurations."
    >
      <form onSubmit={handleSave} className="max-w-4xl space-y-6">
        {saved && (
          <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/30 p-4 text-xs font-bold text-emerald-500 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> Settings updated successfully!
          </div>
        )}

        {/* Prediction Threshold Settings */}
        <GlassCard className="p-8">
          <div className="flex items-center gap-3 border-b border-border/40 pb-4 mb-6">
            <Cpu className="h-5 w-5 text-primary" />
            <div>
              <h3 className="text-base font-bold">LightGBM Machine Learning Thresholds</h3>
              <p className="text-xs text-muted-foreground">
                Adjust delay risk probability sensitivity.
              </p>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                High Delay Risk Threshold (%)
              </label>
              <select
                value={highRiskThreshold}
                onChange={(e) => setHighRiskThreshold(e.target.value)}
                className="w-full rounded-xl border border-input bg-background/70 p-3 text-xs outline-none focus:border-primary focus:shadow-glow"
              >
                <option value="70">70% (Aggressive Trigger)</option>
                <option value="75">75% (Standard FAA Recommended)</option>
                <option value="80">80% (Conservative Trigger)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Automated Passenger Rebooking
              </label>
              <div className="flex items-center gap-3 mt-3">
                <input
                  type="checkbox"
                  id="autoRebook"
                  checked={autoRebookEnabled}
                  onChange={(e) => setAutoRebookEnabled(e.target.checked)}
                  className="h-4 w-4 rounded accent-primary cursor-pointer"
                />
                <label
                  htmlFor="autoRebook"
                  className="text-xs font-medium text-foreground cursor-pointer"
                >
                  Auto-trigger rebooking matching on High Risk flights (&gt;{highRiskThreshold}%)
                </label>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Notification Settings */}
        <GlassCard className="p-8">
          <div className="flex items-center gap-3 border-b border-border/40 pb-4 mb-6">
            <Bell className="h-5 w-5 text-primary" />
            <div>
              <h3 className="text-base font-bold">Automated Notification Triggers</h3>
              <p className="text-xs text-muted-foreground">
                Configure email and SMS dispatch channels.
              </p>
            </div>
          </div>

          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl border border-border/60 bg-background/50">
              <div>
                <p className="font-bold text-foreground">Email Delay Triggers</p>
                <p className="text-muted-foreground">
                  Send real-time delay reasons & lounge vouchers to passengers.
                </p>
              </div>
              <input
                type="checkbox"
                checked={emailAlerts}
                onChange={(e) => setEmailAlerts(e.target.checked)}
                className="h-4 w-4 rounded accent-primary cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl border border-border/60 bg-background/50">
              <div>
                <p className="font-bold text-foreground">SMS & Mobile Notifications</p>
                <p className="text-muted-foreground">
                  Send 1-click mobile rebooking links directly to traveler handsets.
                </p>
              </div>
              <input
                type="checkbox"
                checked={smsAlerts}
                onChange={(e) => setSmsAlerts(e.target.checked)}
                className="h-4 w-4 rounded accent-primary cursor-pointer"
              />
            </div>
          </div>
        </GlassCard>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            className="bg-brand inline-flex items-center justify-center gap-2 rounded-full px-8 py-3.5 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02]"
          >
            <Save className="h-4 w-4" /> Save Configuration
          </button>
        </div>
      </form>
    </PageShell>
  );
}
