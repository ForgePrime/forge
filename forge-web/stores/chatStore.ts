/**
 * Chat store — manages LLM conversations with streaming support.
 *
 * Unlike entity stores (CRUD), the chat store handles:
 * - Multi-conversation state (keyed by session ID)
 * - Real-time token streaming via WebSocket events
 * - Tool call tracking and display
 * - Session token/cost counters
 */
import { create } from "zustand";
import type { ForgeEvent } from "@/lib/ws";
import type { ChatMessage, ChatToolCall, ChatSendResponse, ChatSession } from "@/lib/types";
import { llm } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatConversation {
  sessionId: string;
  contextType: string;
  contextId: string;
  project: string;
  messages: ChatMessage[];
  totalTokensIn: number;
  totalTokensOut: number;
  estimatedCost: number;
  model: string;
}

/** Summary for session list (no full messages). */
export interface ChatSessionSummary {
  session_id: string;
  context_type: string;
  context_id: string;
  project: string;
  model_used: string;
  message_count: number;
  total_tokens_in: number;
  total_tokens_out: number;
  estimated_cost: number;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  /** All active conversations keyed by session ID. */
  conversations: Record<string, ChatConversation>;
  /** Currently active session ID (displayed in the chat panel). */
  activeSessionId: string | null;
  /** True while waiting for LLM response. */
  streaming: boolean;
  /** Last error message. */
  error: string | null;
  /** Session list for sidebar conversations tab. */
  sessionList: ChatSessionSummary[];
  /** True while loading session list. */
  sessionsLoading: boolean;
}

interface ChatActions {
  /** Send a message and get a response. */
  sendMessage: (
    message: string,
    contextType?: string,
    contextId?: string,
    project?: string,
    model?: string | null,
    scopes?: string[],
    disabledCapabilities?: string[],
    fileIds?: string[],
    pageContext?: string,
  ) => Promise<ChatSendResponse | null>;
  /** Start a new conversation (clears active session). */
  startConversation: (contextType: string, contextId: string, project?: string) => void;
  /** Set active session ID. */
  setActiveSession: (sessionId: string | null) => void;
  /** Handle incoming WS event for chat.* events. */
  handleWsEvent: (event: ForgeEvent) => void;
  /** Add a streaming token to the active assistant message. */
  addToken: (sessionId: string, content: string) => void;
  /** Add a tool call event to the active assistant message. */
  addToolCall: (sessionId: string, toolCall: ChatToolCall) => void;
  /** Mark the active streaming message as complete. */
  completeMessage: (sessionId: string, content: string, tokens?: { input: number; output: number }) => void;
  /** Handle streaming error. */
  handleError: (sessionId: string, error: string) => void;
  /** Remove a conversation. */
  removeConversation: (sessionId: string) => void;
  /** Clear error. */
  clearError: () => void;
  /** Load session list from backend. */
  loadSessions: (limit?: number) => Promise<void>;
  /** Resume an existing session (load full messages). */
  resumeSession: (sessionId: string) => Promise<void>;
  /** Delete a session from backend and local state. */
  deleteSession: (sessionId: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let _msgCounter = 0;
function generateMsgId(): string {
  return `msg-${Date.now()}-${++_msgCounter}`;
}

function getOrCreateConversation(
  conversations: Record<string, ChatConversation>,
  sessionId: string,
  contextType = "global",
  contextId = "",
  project = "",
): ChatConversation {
  if (conversations[sessionId]) return conversations[sessionId];
  return {
    sessionId,
    contextType,
    contextId,
    project,
    messages: [],
    totalTokensIn: 0,
    totalTokensOut: 0,
    estimatedCost: 0,
    model: "",
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  conversations: {},
  activeSessionId: null,
  streaming: false,
  error: null,
  sessionList: [],
  sessionsLoading: false,

  sendMessage: async (message, contextType = "global", contextId = "", project = "", model = null, scopes, disabledCapabilities, fileIds, pageContext) => {
    const state = get();
    const sessionId = state.activeSessionId;

    // Add user message to UI immediately (optimistic)
    const userMsg: ChatMessage = {
      id: generateMsgId(),
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };

    // Add placeholder assistant message for streaming
    const assistantMsg: ChatMessage = {
      id: generateMsgId(),
      role: "assistant",
      content: "",
      streaming: true,
      created_at: new Date().toISOString(),
    };

    set((s) => {
      const conv = getOrCreateConversation(
        s.conversations, sessionId ?? "pending", contextType, contextId, project,
      );
      return {
        streaming: true,
        error: null,
        conversations: {
          ...s.conversations,
          [conv.sessionId]: {
            ...conv,
            messages: [...conv.messages, userMsg, assistantMsg],
          },
        },
      };
    });

    try {
      const response = await llm.send({
        message,
        context_type: contextType,
        context_id: contextId,
        project,
        session_id: sessionId,
        model,
        scopes: scopes,
        disabled_capabilities: disabledCapabilities,
        file_ids: fileIds,
        page_context: pageContext,
      });

      // Update conversation with real session ID and response
      set((s) => {
        const oldKey = sessionId ?? "pending";
        const { [oldKey]: oldConv, ...rest } = s.conversations;
        const conv = oldConv ?? getOrCreateConversation(
          s.conversations, response.session_id, contextType, contextId, project,
        );

        // Replace the streaming placeholder with the real response
        const messages = conv.messages.map((m) =>
          m.id === assistantMsg.id
            ? {
                ...m,
                content: response.content,
                toolCalls: response.tool_calls.length > 0 ? response.tool_calls : undefined,
                streaming: false,
              }
            : m,
        );

        return {
          streaming: false,
          activeSessionId: response.session_id,
          conversations: {
            ...rest,
            [response.session_id]: {
              ...conv,
              sessionId: response.session_id,
              messages,
              totalTokensIn: conv.totalTokensIn + response.total_input_tokens,
              totalTokensOut: conv.totalTokensOut + response.total_output_tokens,
              model: response.model,
            },
          },
        };
      });

      return response;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Unknown error";
      set((s) => {
        const key = sessionId ?? "pending";
        const conv = s.conversations[key];
        if (!conv) return { streaming: false, error: errorMsg };

        // Replace streaming placeholder with error
        const messages = conv.messages.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content: `[Error: ${errorMsg}]`, streaming: false }
            : m,
        );

        return {
          streaming: false,
          error: errorMsg,
          conversations: {
            ...s.conversations,
            [key]: { ...conv, messages },
          },
        };
      });
      return null;
    }
  },

  startConversation: (contextType, contextId, project = "") => {
    set({
      activeSessionId: null,
      error: null,
    });
  },

  setActiveSession: (sessionId) => {
    set({ activeSessionId: sessionId, error: null });
  },

  handleWsEvent: (event: ForgeEvent) => {
    const { event: eventType, payload } = event;
    const sessionId = (payload as Record<string, unknown>).session_id as string;
    if (!sessionId) return;

    const state = get();
    // Only process events for conversations we're tracking
    if (!state.conversations[sessionId] && sessionId !== state.activeSessionId) return;

    switch (eventType) {
      case "chat.token": {
        const content = (payload as Record<string, unknown>).content as string;
        if (content) state.addToken(sessionId, content);
        break;
      }
      case "chat.tool_call": {
        const p = payload as Record<string, unknown>;
        state.addToolCall(sessionId, {
          name: p.name as string,
          input: p.input as Record<string, unknown>,
        });
        break;
      }
      case "chat.tool_result": {
        const p = payload as Record<string, unknown>;
        // Update the last tool call with its result
        set((s) => {
          const conv = s.conversations[sessionId];
          if (!conv) return s;
          const messages = [...conv.messages];
          const lastMsg = messages[messages.length - 1];
          if (lastMsg?.role === "assistant" && lastMsg.toolCalls) {
            const toolCalls = [...lastMsg.toolCalls];
            const idx = toolCalls.findIndex((tc) => tc.name === p.name);
            if (idx >= 0) {
              toolCalls[idx] = { ...toolCalls[idx], result: p.result as Record<string, unknown> };
              messages[messages.length - 1] = { ...lastMsg, toolCalls };
            }
          }
          return {
            conversations: { ...s.conversations, [sessionId]: { ...conv, messages } },
          };
        });
        break;
      }
      case "chat.complete": {
        const p = payload as Record<string, unknown>;
        state.completeMessage(sessionId, p.content as string, {
          input: (p.total_input_tokens as number) ?? 0,
          output: (p.total_output_tokens as number) ?? 0,
        });
        break;
      }
      case "chat.error": {
        const p = payload as Record<string, unknown>;
        state.handleError(sessionId, (p.message ?? p.reason ?? "Unknown error") as string);
        break;
      }
    }
  },

  addToken: (sessionId, content) => {
    set((s) => {
      const conv = s.conversations[sessionId];
      if (!conv) return s;
      const messages = [...conv.messages];
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === "assistant" && lastMsg.streaming) {
        messages[messages.length - 1] = {
          ...lastMsg,
          content: lastMsg.content + content,
        };
      }
      return {
        conversations: { ...s.conversations, [sessionId]: { ...conv, messages } },
      };
    });
  },

  addToolCall: (sessionId, toolCall) => {
    set((s) => {
      const conv = s.conversations[sessionId];
      if (!conv) return s;
      const messages = [...conv.messages];
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === "assistant") {
        messages[messages.length - 1] = {
          ...lastMsg,
          toolCalls: [...(lastMsg.toolCalls ?? []), toolCall],
        };
      }
      return {
        conversations: { ...s.conversations, [sessionId]: { ...conv, messages } },
      };
    });
  },

  completeMessage: (sessionId, content, tokens) => {
    set((s) => {
      const conv = s.conversations[sessionId];
      if (!conv) return { streaming: false };
      const messages = conv.messages.map((m) =>
        m.streaming ? { ...m, content: content || m.content, streaming: false } : m,
      );
      return {
        streaming: false,
        conversations: {
          ...s.conversations,
          [sessionId]: {
            ...conv,
            messages,
            totalTokensIn: conv.totalTokensIn + (tokens?.input ?? 0),
            totalTokensOut: conv.totalTokensOut + (tokens?.output ?? 0),
          },
        },
      };
    });
  },

  handleError: (sessionId, error) => {
    set((s) => {
      const conv = s.conversations[sessionId];
      if (!conv) return { streaming: false, error };
      const messages = conv.messages.map((m) =>
        m.streaming ? { ...m, content: `[Error: ${error}]`, streaming: false } : m,
      );
      return {
        streaming: false,
        error,
        conversations: {
          ...s.conversations,
          [sessionId]: { ...conv, messages },
        },
      };
    });
  },

  removeConversation: (sessionId) => {
    set((s) => {
      const { [sessionId]: _, ...rest } = s.conversations;
      return {
        conversations: rest,
        activeSessionId: s.activeSessionId === sessionId ? null : s.activeSessionId,
      };
    });
  },

  clearError: () => set({ error: null }),

  loadSessions: async (limit = 50) => {
    set({ sessionsLoading: true });
    try {
      const result = await llm.listSessions(limit);
      set({ sessionList: result.sessions as ChatSessionSummary[], sessionsLoading: false });
    } catch (e) {
      set({ sessionsLoading: false, error: e instanceof Error ? e.message : "Failed to load sessions" });
    }
  },

  resumeSession: async (sessionId) => {
    try {
      const session: ChatSession = await llm.getSession(sessionId);
      const conv: ChatConversation = {
        sessionId: session.session_id,
        contextType: session.context_type,
        contextId: session.context_id,
        project: session.project,
        messages: session.messages ?? [],
        totalTokensIn: session.total_tokens_in,
        totalTokensOut: session.total_tokens_out,
        estimatedCost: session.estimated_cost,
        model: session.model_used ?? "",
      };
      set((s) => ({
        conversations: { ...s.conversations, [sessionId]: conv },
        activeSessionId: sessionId,
        error: null,
      }));
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to resume session" });
    }
  },

  deleteSession: async (sessionId) => {
    try {
      await llm.deleteSession(sessionId);
      set((s) => {
        const { [sessionId]: _, ...rest } = s.conversations;
        return {
          conversations: rest,
          sessionList: s.sessionList.filter((ss) => ss.session_id !== sessionId),
          activeSessionId: s.activeSessionId === sessionId ? null : s.activeSessionId,
        };
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to delete session" });
    }
  },
}));
