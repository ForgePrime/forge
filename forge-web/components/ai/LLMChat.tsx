"use client";

import { useCallback, useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import Message from "./Message";
import ChatInput from "./ChatInput";

interface LLMChatProps {
  contextType: string;
  contextId: string;
  slug?: string;
  className?: string;
  onError?: (error: string) => void;
}

export default function LLMChat({
  contextType,
  contextId,
  slug = "",
  className = "",
  onError,
}: LLMChatProps) {
  const {
    conversations,
    activeSessionId,
    streaming,
    error,
    sendMessage,
    startConversation,
    clearError,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get current conversation
  const conversation = activeSessionId
    ? conversations[activeSessionId]
    : conversations["pending"];
  const messages = conversation?.messages ?? [];

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content]);

  // Report errors to parent
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  // Start new conversation when context changes
  useEffect(() => {
    startConversation(contextType, contextId, slug);
  }, [contextType, contextId, slug, startConversation]);

  const handleSend = useCallback(
    (message: string, fileIds?: string[]) => {
      clearError();
      sendMessage(message, contextType, contextId, slug, null, undefined, undefined, fileIds);
    },
    [contextType, contextId, slug, sendMessage, clearError],
  );

  // Token counter
  const totalTokens = (conversation?.totalTokensIn ?? 0) + (conversation?.totalTokensOut ?? 0);

  return (
    <div className={`flex flex-col bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">AI Chat</span>
          {contextType !== "global" && (
            <span className="rounded bg-forge-100 px-2 py-0.5 text-xs font-medium text-forge-700">
              {contextType} {contextId}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {conversation?.model && (
            <span title="Model">{conversation.model.split("-").slice(0, 2).join("-")}</span>
          )}
          {totalTokens > 0 && (
            <span title="Total tokens used">{totalTokens.toLocaleString()} tokens</span>
          )}
          {streaming && (
            <span className="flex items-center gap-1 text-forge-600">
              <span className="animate-pulse">●</span> Streaming
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px]">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            {contextType === "global"
              ? "Ask me anything..."
              : `Ask me anything about this ${contextType}...`}
          </div>
        ) : (
          messages.map((msg) => <Message key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="border-t border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">
          {error}
          <button onClick={clearError} className="ml-2 underline hover:no-underline">
            dismiss
          </button>
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={streaming}
        sessionId={activeSessionId}
        placeholder={
          contextType === "global"
            ? "Type a message or drop files..."
            : `Ask about this ${contextType}...`
        }
      />
    </div>
  );
}
