"use client";

import React, { useEffect, useState } from "react";
import { getInsights, getTickets, getOrders } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface Insight {
  summary: Record<string, number>;
  sla_alerts: Array<Record<string, unknown>>;
  surge_alerts: Array<Record<string, unknown>>;
  issue_clusters: Array<Record<string, unknown>>;
  carrier_fault_orders: Array<Record<string, unknown>>;
}

export default function IssueRadar() {
  const { token } = useAuth();
  const [insights, setInsights] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    getInsights(token)
      .then(setInsights)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 80, marginBottom: 12 }} />
        ))}
      </div>
    );
  }

  if (!insights) return null;

  const { summary, sla_alerts, surge_alerts, issue_clusters, carrier_fault_orders } = insights;

  return (
    <div style={{ padding: 20, overflowY: "auto", height: "100%" }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
        🔍 Issue Radar
      </h2>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>
        Proactive detections as of dataset snapshot · Aug 16, 2026 11:00 IST
      </p>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 24 }}>
        {[
          { label: "Open Tickets", val: summary.open_tickets, icon: "🎫", color: "var(--text-accent)" },
          { label: "SLA Breaches", val: summary.sla_breaches, icon: "🔴", color: "var(--sev-p1)" },
          { label: "Approaching SLA", val: summary.sla_approaching, icon: "🟡", color: "var(--sev-p2)" },
          { label: "Account Surges", val: summary.account_surges, icon: "📈", color: "#f472b6" },
          { label: "Issue Clusters", val: summary.pattern_clusters, icon: "🔗", color: "var(--brand-accent)" },
          { label: "Carrier Faults", val: summary.unresolved_carrier_faults, icon: "🚚", color: "var(--sev-p2)" },
        ].map((s, i) => (
          <div key={i} style={{
            background: "var(--bg-glass)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "14px 16px",
          }}>
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>{s.icon} {s.label}</p>
            <p style={{ fontSize: 26, fontWeight: 800, color: s.color }}>{s.val}</p>
          </div>
        ))}
      </div>

      {/* SLA Alerts */}
      {sla_alerts.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--sev-p1)" }}>
            🔴 SLA Alerts ({sla_alerts.length})
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sla_alerts.map((alert, i) => (
              <div key={i} className={`insight-card ${alert.breached ? "insight-card-critical" : "insight-card-warning"}`}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 14, marginRight: 8 }}>
                      {String(alert.ticket_id)}
                    </span>
                    <span className={`badge-${String(alert.priority).toLowerCase()}`} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.3)", color: "#a5b4fc" }}>
                      {String(alert.priority)}
                    </span>
                    {Boolean(alert.breached) && <span style={{ marginLeft: 6, fontSize: 11, color: "var(--sev-p1)", fontWeight: 700 }}>● BREACHED</span>}
                    {Boolean(alert.approaching) && !Boolean(alert.breached) && <span style={{ marginLeft: 6, fontSize: 11, color: "var(--sev-p2)", fontWeight: 700 }}>● APPROACHING</span>}
                  </div>
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {String(alert.account_name)} · Assigned: {String(alert.assigned_to)}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                  {String(alert.subject)}
                </p>
                <p style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Elapsed: <strong style={{ color: "var(--text-primary)" }}>{String(alert.elapsed_minutes)} min</strong>
                  {" "}/ SLA target: <strong style={{ color: "var(--text-primary)" }}>{String(alert.sla_target_minutes)} min</strong>
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Surge Alerts */}
      {surge_alerts.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#f472b6" }}>
            📈 Account Surges
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {surge_alerts.map((s, i) => (
              <div key={i} className="insight-card insight-card-warning">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong style={{ fontSize: 14 }}>{String(s.account_name)}</strong>
                  <span style={{ fontSize: 12, color: "var(--sev-p2)" }}>{String(s.open_ticket_count)} open tickets</span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                  {(s.tickets as string[]).join(", ")}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Issue Clusters */}
      {issue_clusters.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--brand-accent)" }}>
            🔗 Issue Patterns
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {issue_clusters.map((c, i) => (
              <div key={i} className="insight-card">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <strong style={{ fontSize: 13 }}>{String(c.pattern_label)}</strong>
                  <span style={{ fontSize: 11, color: "var(--sev-p2)" }}>
                    {String(c.ticket_count)} ticket{Number(c.ticket_count) > 1 ? "s" : ""}
                    {c.multi_customer ? " · Multi-customer ⚠️" : ""}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {(c.tickets as string[]).join(", ")}
                  {" — "}{(c.accounts_affected as string[]).length} account(s) affected
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Carrier Fault Orders */}
      {carrier_fault_orders.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--sev-p2)" }}>
            🚚 Unresolved Carrier Faults
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {carrier_fault_orders.map((o, i) => (
              <div key={i} className="insight-card insight-card-warning">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{String(o.order_id)}</strong>
                  <span style={{ fontSize: 12, color: "var(--sev-p2)" }}>{String(o.delay_hours)}h delay</span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                  {String(o.account_name)} · {String(o.carrier)} · Fee: ₹{String(o.shipment_fee_inr)}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
