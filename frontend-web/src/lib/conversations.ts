import type { ChatResponse } from "@/types/api";

export const CONVERSATIONS_STORAGE_KEY = "finrag.conversations";
export const CONVERSATIONS_CHANGED_EVENT = "finrag.conversations.changed";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: ChatResponse["sources"];
  intent?: ChatResponse["intent"];
};

export type Conversation = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

export function createConversationTitle(message: string): string {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) return "새 대화";
  return normalized.length > 18 ? `${normalized.slice(0, 18)}...` : normalized;
}

export function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function conversationsStorageKey(username?: string | null): string {
  const normalized = username?.trim();
  return normalized ? `${CONVERSATIONS_STORAGE_KEY}.${normalized}` : `${CONVERSATIONS_STORAGE_KEY}.anonymous`;
}

function isConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<Conversation>;
  return (
    typeof item.id === "string" &&
    typeof item.title === "string" &&
    Array.isArray(item.messages) &&
    typeof item.createdAt === "string" &&
    typeof item.updatedAt === "string"
  );
}

export function loadConversations(username?: string | null): Conversation[] {
  try {
    const raw = localStorage.getItem(conversationsStorageKey(username));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isConversation).sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[], username?: string | null): Conversation[] {
  const sorted = [...conversations].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt)).slice(0, 10);
  localStorage.setItem(conversationsStorageKey(username), JSON.stringify(sorted));
  window.dispatchEvent(new Event(CONVERSATIONS_CHANGED_EVENT));
  return sorted;
}
