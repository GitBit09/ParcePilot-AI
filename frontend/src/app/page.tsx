"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const DEMO_ACCOUNTS = [
  { label: "Northstar Logistics (Customer)", email: "northstar@parcelPilot.com", password: "northstar123", icon: "🏭" },
  { label: "LumenWorks (Customer)", email: "lumenworks@parcelPilot.com", password: "lumenworks123", icon: "💡" },
  { label: "Beacon Retail (Customer)", email: "beacon@parcelPilot.com", password: "beacon123", icon: "🏪" },
  { label: "Axis Labs (Customer)", email: "axislabs@parcelPilot.com", password: "axislabs123", icon: "🔬" },
  { label: "Rohit — Support Agent (Staff)", email: "rohit@parcelPilot.com", password: "staff123", icon: "🛡️" },
  { label: "Maya — Support Agent (Staff)", email: "maya@parcelPilot.com", password: "staff123", icon: "🛡️" },
  { label: "Priya Mehta — CSM (Staff)", email: "priya@parcelPilot.com", password: "staff123", icon: "👤" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/chat");
    } catch {
      setError("Invalid credentials. Use a demo account below.");
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (acc: typeof DEMO_ACCOUNTS[0]) => {
    setLoading(true);
    setError("");
    try {
      await login(acc.email, acc.password);
      router.push("/chat");
    } catch {
      setError("Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, position: "relative" }}>
      <div className="bg-mesh" />
      <div style={{ width: "100%", maxWidth: 480, position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{
            width: 64, height: 64, borderRadius: "50%",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 32, margin: "0 auto 16px", boxShadow: "0 0 40px rgba(99,102,241,0.5)",
          }}>📦</div>
          <h1 className="gradient-text" style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>
            ParcelPilot AI
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
            Intelligent logistics support powered by AI
          </p>
        </div>

        {/* Login form */}
        <div className="glass" style={{ padding: 32, marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Sign In</h2>
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Email
              </label>
              <input
                id="login-email"
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@parcelPilot.com"
                required
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Password
              </label>
              <input
                id="login-password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            {error && (
              <p style={{ color: "var(--sev-p1)", fontSize: 13, marginBottom: 16 }}>{error}</p>
            )}
            <button
              id="login-btn"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: "100%", justifyContent: "center", height: 46 }}
            >
              {loading ? <span className="spinner" /> : "Sign In →"}
            </button>
          </form>
        </div>

        {/* Quick login */}
        <div className="glass" style={{ padding: 24 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
            ✨ Try it instantly
          </p>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 14 }}>
            Click any account below — no password needed
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {DEMO_ACCOUNTS.map((acc, i) => (
              <button
                key={i}
                id={`quick-login-${i}`}
                onClick={() => quickLogin(acc)}
                disabled={loading}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 14px",
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer", width: "100%",
                  color: "var(--text-secondary)", fontSize: 13,
                  fontFamily: "var(--font-sans)",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border-default)";
                  (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border-subtle)";
                  (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
                }}
              >
                <span style={{ fontSize: 18 }}>{acc.icon}</span>
                <span>{acc.label}</span>
                <span style={{
                  marginLeft: "auto", fontSize: 10,
                  padding: "2px 8px", borderRadius: 999,
                  background: acc.icon === "🛡️" || acc.icon === "👤"
                    ? "rgba(6,182,212,0.15)" : "rgba(99,102,241,0.15)",
                  border: `1px solid ${acc.icon === "🛡️" || acc.icon === "👤" ? "rgba(6,182,212,0.3)" : "rgba(99,102,241,0.3)"}`,
                  color: acc.icon === "🛡️" || acc.icon === "👤" ? "#67e8f9" : "var(--text-accent)",
                  fontWeight: 600,
                }}>
                  {acc.icon === "🛡️" || acc.icon === "👤" ? "STAFF" : "CUSTOMER"}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
