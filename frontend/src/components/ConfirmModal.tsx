"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { PendingAction } from "@/lib/api";

interface ConfirmModalProps {
  action: PendingAction;
  onConfirm: () => void;
  onDeny: () => void;
  inline?: boolean;
}

export function ConfirmModal({ action, onConfirm, onDeny, inline }: ConfirmModalProps) {
  const content = (
    <div style={{
      background: "rgba(245,158,11,0.05)",
      border: "1px solid rgba(245, 158, 11, 0.35)",
      borderRadius: "var(--radius-lg)",
      padding: 20,
      maxWidth: 480,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <span style={{ fontSize: 22 }}>⚡</span>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--sev-p2)", marginBottom: 2 }}>
            Action Confirmation Required
          </p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{action.summary}</p>
        </div>
      </div>

      {/* Message */}
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: 14,
        marginBottom: 16,
        fontSize: 13,
        color: "var(--text-primary)",
        lineHeight: 1.6,
      }}>
        <ReactMarkdown>{action.confirmation_message}</ReactMarkdown>
      </div>

      {/* Buttons */}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button
          id={`deny-${action.action_type}`}
          className="btn btn-ghost"
          onClick={onDeny}
          style={{ fontSize: 13, padding: "8px 18px" }}
        >
          Cancel
        </button>
        <button
          id={`confirm-${action.action_type}`}
          className="btn btn-success"
          onClick={onConfirm}
          style={{ fontSize: 13, padding: "8px 18px" }}
        >
          ✅ Confirm & Execute
        </button>
      </div>
    </div>
  );

  if (inline) {
    return <div style={{ marginLeft: 36 }}>{content}</div>;
  }

  return (
    <div className="modal-overlay">
      <div className="modal-card">{content}</div>
    </div>
  );
}
