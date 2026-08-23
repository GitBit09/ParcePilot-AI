"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { MessageBubble } from "./MessageBubble";
import { Message, PendingAction, SSEEvent, streamChat, confirmAction } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const SUGGESTIONS_CUSTOMER: Record<string, string[]> = {
  "ACCT-001": [
    "Can I cancel ORD-1001 without a cancellation fee?",
    "What are my open support tickets?",
    "What is my P1 response time SLA?",
    "Show me all my recent orders",
  ],
  "ACCT-002": [
    "My pickup on ORD-2002 is 5 hours late due to carrier fault. Do I get a credit?",
    "Why is my bulk CSV upload failing?",
    "What is my cancellation policy?",
    "What is the service credit amount for late pickup?",
  ],
  "ACCT-003": [
    "How do I change my billing contact?",
    "Can I cancel ORD-3001?",
    "What is the standard cancellation policy?",
  ],
  "ACCT-004": [
    "What should I do about TKT-505 — API key exposure?",
    "What is my P1 SLA response time?",
  ],
  DEFAULT: [
    "What is the cancellation policy?",
    "How do service credits work?",
    "What are support severity levels?",
  ],
};

const SUGGESTIONS_STAFF = [
  "Show me all open tickets and their SLA status",
  "Escalate TKT-501 to P1 priority",
  "Can Northstar cancel ORD-1001 without a fee? Explain why.",
  "What is the correct answer for TKT-450's historical resolution?",
  "A pickup is 3 hours late due to carrier fault for LumenWorks — do they get a credit?",
  "Create a follow-up task for TKT-505",
];

export default function ChatInterface({ mode }: { mode: "customer" | "staff" }) {
  const { user, token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const suggestions =
    mode === "staff"
      ? SUGGESTIONS_STAFF
      : SUGGESTIONS_CUSTOMER[user?.account_id || "DEFAULT"] || SUGGESTIONS_CUSTOMER.DEFAULT;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading || !token) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      const assistantMsg: Message = {
        role: "assistant",
        content: "",
        toolCalls: [],
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      try {
        const history = [...messages, userMsg];
        let pendingAction: PendingAction | null = null;
        let fullText = "";

        for await (const event of streamChat(history, token)) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = { ...updated[updated.length - 1] };

            if (event.type === "tool_start") {
              last.toolCalls = [
                ...(last.toolCalls || []),
                { tool: event.tool!, args: event.args || {} },
              ];
            } else if (event.type === "text") {
              fullText += event.content || "";
              last.content = fullText;
            } else if (event.type === "pending_action") {
              pendingAction = event.action!;
              last.pendingAction = pendingAction;
              last.content = fullText;
            } else if (event.type === "done") {
              last.isStreaming = false;
            }

            updated[updated.length - 1] = last;
            return updated;
          });
        }
      } catch (err) {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "⚠️ Something went wrong. Please try again.",
            isStreaming: false,
          };
          return updated;
        });
      } finally {
        setIsLoading(false);
      }
    },
    [messages, token, isLoading]
  );

  const handleConfirmAction = async (action: PendingAction) => {
    if (!token) return;
    try {
      const result = await confirmAction(action, token);
      setMessages((prev) => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.pendingAction = undefined;
        last.content =
          (last.content || "") +
          `\n\n✅ **Action executed successfully.**\n${result.message || ""}`;
        updated[updated.length - 1] = last;
        return updated;
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.pendingAction = undefined;
        last.content = (last.content || "") + "\n\n❌ Action failed. Please try again.";
        updated[updated.length - 1] = last;
        return updated;
      });
    }
  };

  const handleDenyAction = () => {
    setMessages((prev) => {
      const updated = [...prev];
      const last = { ...updated[updated.length - 1] };
      last.pendingAction = undefined;
      last.content = (last.content || "") + "\n\n*Action cancelled by user.*";
      updated[updated.length - 1] = last;
      return updated;
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      position: "relative",
    }}>
      {/* Messages area */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "24px 20px",
        display: "flex",
        flexDirection: "column",
      }}>
        {isEmpty ? (
          <div style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 24,
            paddingBottom: 60,
          }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>
                {mode === "staff" ? "🛡️" : "📦"}
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
                {mode === "staff" ? "Internal Operations AI" : "ParcelPilot Support AI"}
              </h2>
              <p style={{ color: "var(--text-secondary)", fontSize: 14, maxWidth: 380, lineHeight: 1.6 }}>
                {mode === "staff"
                  ? "Ask about any account, ticket, or policy. Full data access with source citations."
                  : `Hello, ${user?.display_name}! Ask me anything about your orders, tickets, or policies.`}
              </p>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
              width: "100%",
              maxWidth: 600,
            }}>
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  id={`suggestion-${i}`}
                  onClick={() => sendMessage(s)}
                  style={{
                    background: "var(--bg-glass)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    padding: "12px 14px",
                    color: "var(--text-secondary)",
                    fontSize: 13,
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.2s ease",
                    lineHeight: 1.5,
                    fontFamily: "var(--font-sans)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--brand-primary)";
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border-subtle)";
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble
                key={i}
                message={msg}
                onConfirmAction={handleConfirmAction}
                onDenyAction={handleDenyAction}
              />
            ))}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: "16px 20px",
        borderTop: "1px solid var(--border-subtle)",
        background: "var(--bg-glass)",
        backdropFilter: "blur(20px)",
      }}>
        <div style={{
          display: "flex",
          gap: 10,
          alignItems: "flex-end",
          maxWidth: 900,
          margin: "0 auto",
        }}>
          <textarea
            ref={inputRef}
            id="chat-input"
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === "staff"
                ? "Ask about tickets, accounts, orders, or execute actions..."
                : "Ask about your orders, policies, or support..."
            }
            rows={1}
            style={{
              resize: "none",
              minHeight: 46,
              maxHeight: 160,
              overflowY: "auto",
              lineHeight: 1.5,
              paddingTop: 12,
              paddingBottom: 12,
            }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 160) + "px";
            }}
          />
          <button
            id="send-btn"
            className="btn btn-primary"
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
            style={{ height: 46, padding: "0 20px", flexShrink: 0 }}
          >
            {isLoading ? <span className="spinner" /> : "Send →"}
          </button>
        </div>
        <p style={{
          textAlign: "center",
          fontSize: 11,
          color: "var(--text-muted)",
          marginTop: 8,
        }}>
          Sources cited • Deprecated docs excluded • Actions require confirmation
        </p>
      </div>
    </div>
  );
}
