const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  user_id: string;
  account_id: string | null;
  account_name: string | null;
  role: "customer" | "staff";
  display_name: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  pendingAction?: PendingAction;
  isStreaming?: boolean;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface PendingAction {
  action_type: string;
  summary: string;
  details: Record<string, unknown>;
  confirmation_message: string;
}

export interface SSEEvent {
  type: "tool_start" | "tool_result" | "text" | "pending_action" | "done";
  tool?: string;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  content?: string;
  action?: PendingAction;
  tool_calls?: ToolCall[];
}

export async function login(
  email: string,
  password: string
): Promise<{ token: string; user: User }> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  return res.json();
}

export async function getMe(token: string): Promise<User> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

export async function* streamChat(
  messages: Message[],
  token: string
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  });

  if (!res.ok) throw new Error("Chat request failed");

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as SSEEvent;
          yield event;
        } catch {
          // ignore malformed
        }
      }
    }
  }
}

export async function confirmAction(
  action: PendingAction,
  token: string
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_URL}/chat/confirm-action`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(action),
  });
  if (!res.ok) throw new Error("Action failed");
  return res.json();
}

export async function getInsights(token: string) {
  const res = await fetch(`${API_URL}/insights`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load insights");
  return res.json();
}

export async function getTickets(token: string) {
  const res = await fetch(`${API_URL}/data/tickets`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load tickets");
  return res.json();
}

export async function getOrders(token: string) {
  const res = await fetch(`${API_URL}/data/orders`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load orders");
  return res.json();
}
