"use client";

import React, { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { ToolBadge } from "./ToolBadge";
import { ConfirmModal } from "./ConfirmModal";
import { Message, PendingAction } from "@/lib/api";

interface MessageBubbleProps {
  message: Message;
  onConfirmAction?: (action: PendingAction) => void;
  onDenyAction?: () => void;
}

export function MessageBubble({
  message,
  onConfirmAction,
  onDenyAction,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <div className="message-user">{message.content}</div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
      {/* Avatar + label */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, flexShrink: 0,
        }}>
          🤖
        </div>
        <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 600 }}>
          ParcelPilot AI
        </span>
      </div>

      {/* Tool call badges */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginLeft: 36 }}>
          {message.toolCalls.map((tc, i) => (
            <ToolBadge key={i} toolName={tc.tool} done={!message.isStreaming} />
          ))}
        </div>
      )}

      {/* Typing indicator while streaming with no content yet */}
      {message.isStreaming && !message.content && !message.pendingAction && (
        <div className="message-assistant" style={{ marginLeft: 36, display: "flex", gap: 5, alignItems: "center" }}>
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      )}

      {/* Main text content */}
      {message.content && (
        <div className="message-assistant prose" style={{ marginLeft: 36 }}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
          {message.isStreaming && (
            <span style={{
              display: "inline-block", width: 2, height: "1em",
              background: "var(--brand-primary)", marginLeft: 2,
              animation: "blink 0.8s ease-in-out infinite", verticalAlign: "text-bottom",
            }} />
          )}
        </div>
      )}

      {/* Pending action confirmation */}
      {message.pendingAction && onConfirmAction && (
        <ConfirmModal
          action={message.pendingAction}
          onConfirm={() => onConfirmAction(message.pendingAction!)}
          onDeny={onDenyAction || (() => {})}
          inline
        />
      )}
    </div>
  );
}
