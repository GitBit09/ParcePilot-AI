"use client";

import React from "react";

const TOOL_CONFIG: Record<string, { label: string; icon: string; cls: string }> = {
  doc_search: { label: "Searching Documents", icon: "📄", cls: "tool-badge-doc" },
  get_account: { label: "Looking Up Account", icon: "🏢", cls: "tool-badge-data" },
  get_order: { label: "Fetching Order", icon: "📦", cls: "tool-badge-data" },
  get_orders_for_account: { label: "Loading Orders", icon: "📦", cls: "tool-badge-data" },
  get_ticket: { label: "Fetching Ticket", icon: "🎫", cls: "tool-badge-data" },
  get_tickets_for_account: { label: "Loading Tickets", icon: "🎫", cls: "tool-badge-data" },
  get_all_open_tickets: { label: "All Open Tickets", icon: "🎫", cls: "tool-badge-data" },
  get_all_orders: { label: "All Orders", icon: "📦", cls: "tool-badge-data" },
  prepare_escalation: { label: "Preparing Escalation", icon: "⚡", cls: "tool-badge-action" },
  execute_escalation: { label: "Escalating Ticket", icon: "⚡", cls: "tool-badge-action" },
  prepare_ticket_update: { label: "Preparing Update", icon: "📝", cls: "tool-badge-action" },
  execute_ticket_update: { label: "Updating Ticket", icon: "📝", cls: "tool-badge-action" },
  prepare_followup_task: { label: "Creating Task", icon: "📌", cls: "tool-badge-action" },
  execute_followup_task: { label: "Saving Task", icon: "📌", cls: "tool-badge-action" },
};

export function ToolBadge({
  toolName,
  done = false,
}: {
  toolName: string;
  done?: boolean;
}) {
  const config = TOOL_CONFIG[toolName] || {
    label: toolName,
    icon: "🔧",
    cls: "tool-badge-doc",
  };

  return (
    <span
      className={`tool-badge ${config.cls}`}
      style={{ animation: done ? "none" : undefined, opacity: done ? 0.7 : 1 }}
    >
      <span>{config.icon}</span>
      <span>{done ? `${config.label} ✓` : config.label}</span>
      {!done && <span className="spinner" style={{ width: 10, height: 10 }} />}
    </span>
  );
}
