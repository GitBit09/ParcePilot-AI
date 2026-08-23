"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import IssueRadar from "@/components/IssueRadar";
import ChatInterface from "@/components/ChatInterface";
import { useAuth } from "@/lib/auth-context";
import { getTickets, getOrders } from "@/lib/api";

type Tab = "radar" | "chat" | "tickets" | "orders";

export default function OpsPage() {
  const { user, token, logout, isLoading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("radar");
  const [tickets, setTickets] = useState<Record<string, unknown>[]>([]);
  const [orders, setOrders] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    if (!isLoading && !user) { router.push("/"); return; }
    if (!isLoading && user && user.role !== "staff") router.push("/chat");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (!token) return;
    getTickets(token).then(setTickets).catch(console.error);
    getOrders(token).then(setOrders).catch(console.error);
  }, [token]);

  if (isLoading || !user) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <span className="spinner" />
    </div>
  );

  const STATUS_COLORS: Record<string, string> = {
    open: "#10b981", escalated: "#ef4444", closed: "#6b7280",
  };

  const CARRIER_FAULT_COLOR = "#f59e0b";

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="bg-mesh" />

      {/* Nav */}
      <nav style={{
        height: 58, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: "1px solid var(--border-subtle)",
        background: "var(--bg-glass)", backdropFilter: "blur(20px)",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 22 }}>📦</div>
          <span style={{ fontWeight: 700, fontSize: 15 }}>ParcelPilot</span>
          <span style={{
            fontSize: 11, padding: "2px 8px", borderRadius: 999,
            background: "rgba(6,182,212,0.15)", border: "1px solid rgba(6,182,212,0.3)",
            color: "#67e8f9", fontWeight: 600,
          }}>STAFF OPS</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/chat" id="chat-nav-link" style={{
            fontSize: 13, color: "var(--text-secondary)", textDecoration: "none",
            padding: "6px 12px", borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
          }}>
            💬 Chat
          </Link>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{user.display_name}</span>
          <button
            id="logout-ops-btn"
            onClick={() => { logout(); router.push("/"); }}
            className="btn btn-ghost"
            style={{ fontSize: 12, padding: "6px 14px" }}
          >
            Sign out
          </button>
        </div>
      </nav>

      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative", zIndex: 1 }}>
        {/* Sidebar tabs */}
        <aside style={{
          width: 200, flexShrink: 0, padding: "20px 12px",
          borderRight: "1px solid var(--border-subtle)",
          background: "var(--bg-glass)", backdropFilter: "blur(20px)",
        }}>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 10, paddingLeft: 4, fontWeight: 600, letterSpacing: "0.05em" }}>
            VIEWS
          </p>
          {([
            ["radar", "🔍 Issue Radar", null],
            ["chat", "💬 AI Assistant", null],
            ["tickets", "🎫 All Tickets", tickets.length],
            ["orders", "📦 All Orders", orders.length],
          ] as [Tab, string, number | null][]).map(([tab, label, count]) => (
            <button
              key={tab}
              id={`tab-${tab}`}
              onClick={() => setActiveTab(tab)}
              className={`nav-item ${activeTab === tab ? "active" : ""}`}
              style={{ width: "100%", marginBottom: 4, border: "none", background: activeTab === tab ? "rgba(99,102,241,0.15)" : "transparent", justifyContent: "space-between" }}
            >
              <span>{label}</span>
              {count !== null && count > 0 && (
                <span style={{
                  fontSize: 11, fontWeight: 700,
                  background: "rgba(45,74,138,0.12)",
                  border: "1px solid var(--border-default)",
                  color: "var(--brand-primary)",
                  borderRadius: "var(--radius-full)",
                  padding: "1px 7px",
                  minWidth: 22,
                  textAlign: "center",
                }}>
                  {count}
                </span>
              )}
            </button>
          ))}
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, overflow: "auto" }}>
          {activeTab === "radar" && <IssueRadar />}
          {activeTab === "chat" && (
            <div style={{ height: "100%" }}>
              <ChatInterface mode="staff" />
            </div>
          )}
          {activeTab === "tickets" && (
            <div style={{ padding: 24 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>
                🎫 All Open Tickets ({tickets.length})
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {tickets.map((t, i) => (
                  <div key={i} className="insight-card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <strong style={{ fontSize: 14 }}>{String(t.ticket_id)}</strong>
                        <span style={{
                          fontSize: 11, padding: "1px 8px", borderRadius: 999,
                          background: `${STATUS_COLORS[String(t.status)] || "#6b7280"}22`,
                          border: `1px solid ${STATUS_COLORS[String(t.status)] || "#6b7280"}44`,
                          color: STATUS_COLORS[String(t.status)] || "#9ca3af",
                        }}>
                          {String(t.status).toUpperCase()}
                        </span>
                      </div>
                      <div style={{ textAlign: "right", fontSize: 12, color: "var(--text-muted)" }}>
                        <div>{String(t.account_name || t.account_id)} · {String(t.plan || "")}</div>
                        <div>Assigned: {String(t.assigned_to)} · {String(t.channel)}</div>
                      </div>
                    </div>
                    <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{String(t.subject)}</p>
                    <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{String(t.description)}</p>
                    {Boolean(t.historical_resolution) && (
                      <p style={{ fontSize: 11, color: "var(--sev-p2)", marginTop: 6, borderTop: "1px solid var(--border-subtle)", paddingTop: 6 }}>
                        &#x26A0;&#xFE0F; Historical resolution (may be wrong): {String(t.historical_resolution)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {activeTab === "orders" && (
            <div style={{ padding: 24 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>
                📦 All Orders ({orders.length})
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {orders.map((o, i) => (
                  <div key={i} className="insight-card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <strong style={{ fontSize: 14 }}>{String(o.order_id)}</strong>
                        <span style={{
                          fontSize: 11, padding: "1px 8px", borderRadius: 999,
                          background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)",
                          color: "var(--text-accent)",
                        }}>{String(o.status)}</span>
                        {Boolean(o.carrier_fault) ? (
                          <span style={{ fontSize: 11, color: CARRIER_FAULT_COLOR, fontWeight: 700 }}>&#x26A0; CARRIER FAULT</span>
                        ) : null}
                      </div>
                      <div style={{ textAlign: "right", fontSize: 12, color: "var(--text-muted)" }}>
                        <div>{String(o.account_name || o.account_id)}</div>
                        <div>₹{String(o.shipment_fee_inr)} · {String(o.carrier)}</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 20 }}>
                      <span>Booked: {String(o.booked_at)}</span>
                      <span>Window: {String(o.pickup_window_start)} → {String(o.pickup_window_end)}</span>
                      {Boolean(o.cancellation_requested_at) && (
                        <span style={{ color: "var(--sev-p2)" }}>Cancel requested: {String(o.cancellation_requested_at)}</span>
                      )}
                    </div>
                    {Boolean(o.notes) && (
                      <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{String(o.notes)}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
