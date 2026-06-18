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

const MAX_CONVERSATION_TITLE_LENGTH = 28;
const QUESTION_TAIL_PATTERNS = [
  /\s*어떻게\s*(?:보나요|봐요|봐|보십니까|볼까요|생각해요|생각해|생각하나요)$/i,
  /\s*(?:알려\s*줘|알려주세요|설명해\s*줘|설명해주세요|말해\s*줘|말해주세요)$/i,
  /\s*(?:어떤가요|어때요|어때|궁금해요|궁금합니다)$/i,
  /\s*(?:인가요|일까요|인가|입니까|인가요|나요|까요)$/i,
];

function removeQuestionTail(message: string): string {
  let title = message.trim().replace(/[?!？]+$/g, "").trim();
  let previous = "";
  while (title && title !== previous) {
    previous = title;
    for (const pattern of QUESTION_TAIL_PATTERNS) {
      title = title.replace(pattern, "").trim();
    }
  }
  return title || message;
}

function clampTitleAtWordBoundary(title: string): string {
  if (title.length <= MAX_CONVERSATION_TITLE_LENGTH) return title;

  const words = title.split(" ");
  if (words.length === 1) {
    return title.slice(0, MAX_CONVERSATION_TITLE_LENGTH).trim();
  }

  const selected: string[] = [];
  for (const word of words) {
    const candidate = [...selected, word].join(" ");
    if (candidate.length > MAX_CONVERSATION_TITLE_LENGTH) break;
    selected.push(word);
  }
  return selected.length > 0 ? selected.join(" ") : title.slice(0, MAX_CONVERSATION_TITLE_LENGTH).trim();
}

export function createConversationTitle(message: string): string {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) return "새 대화";
  return clampTitleAtWordBoundary(removeQuestionTail(normalized));
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
