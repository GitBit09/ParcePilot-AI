"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ChatInterface from "@/components/ChatInterface";
import { useAuth } from "@/lib/auth-context";

export default function ChatPage() {
  const { user, token, logout, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.push("/");
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!user) return null;

  const isStaff = user.role === "staff";

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", position: "relative" }}>
      <div className="bg-mesh" />

      {/* Top Nav */}
      <nav style={{
        height: 58, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: "1px solid var(--border-subtle)",
        background: "var(--bg-glass)", backdropFilter: "blur(20px)",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 22 }}>📦</div>
          <div>
            <span style={{ fontWeight: 700, fontSize: 15 }}>ParcelPilot AI</span>
            <span style={{
              marginLeft: 10, fontSize: 11, padding: "2px 8px", borderRadius: 999,
              background: isStaff ? "rgba(6,182,212,0.15)" : "rgba(99,102,241,0.15)",
              border: `1px solid ${isStaff ? "rgba(6,182,212,0.3)" : "rgba(99,102,241,0.3)"}`,
              color: isStaff ? "#67e8f9" : "var(--text-accent)", fontWeight: 600,
            }}>
              {isStaff ? "STAFF" : "CUSTOMER"}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {isStaff && (
            <Link
              id="ops-nav-link"
              href="/ops"
              style={{
                fontSize: 13, color: "var(--text-secondary)", textDecoration: "none",
                padding: "6px 12px", borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)", transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-primary)";
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--border-default)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-secondary)";
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--border-subtle)";
              }}
            >
              🔍 Ops Dashboard
            </Link>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)" }}>
            <span style={{ fontSize: 18 }}>{isStaff ? "🛡️" : "👤"}</span>
            <span>{user.display_name}</span>
            {!isStaff && user.account_name && (
              <span style={{ color: "var(--text-muted)" }}>· {user.account_name}</span>
            )}
          </div>
          <button
            id="logout-btn"
            onClick={() => { logout(); router.push("/"); }}
            className="btn btn-ghost"
            style={{ fontSize: 12, padding: "6px 14px" }}
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* Chat area */}
      <div style={{ flex: 1, position: "relative", zIndex: 1, overflow: "hidden", display: "flex" }}>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <ChatInterface mode={isStaff ? "staff" : "customer"} />
        </div>
      </div>
    </div>
  );
}
