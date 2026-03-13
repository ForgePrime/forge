"use client";

import { useState, useMemo, useCallback } from "react";

// ---------------------------------------------------------------------------
// Tokenizer — regex-based JSON syntax highlighting
// ---------------------------------------------------------------------------

type TokenType = "key" | "string" | "number" | "boolean" | "null" | "punct";

interface Token {
  type: TokenType;
  value: string;
}

/**
 * Tokenize a JSON string into colored segments.
 * Handles: keys, strings, numbers, booleans, null, and punctuation.
 */
function tokenizeLine(line: string): Token[] {
  const tokens: Token[] = [];
  // Match JSON tokens in order: strings (with key detection), numbers, booleans, null, punctuation
  const re = /("(?:[^"\\]|\\.)*")\s*(:)?|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(\btrue\b|\bfalse\b)|(\bnull\b)|([{}[\]:,])|(\s+)/g;
  let match: RegExpExecArray | null;
  let lastIndex = 0;

  while ((match = re.exec(line)) !== null) {
    // Unmatched text before this token
    if (match.index > lastIndex) {
      tokens.push({ type: "punct", value: line.slice(lastIndex, match.index) });
    }
    lastIndex = re.lastIndex;

    if (match[1] !== undefined) {
      // String or key
      if (match[2] !== undefined) {
        // It's a key (followed by colon)
        tokens.push({ type: "key", value: match[1] });
        tokens.push({ type: "punct", value: ":" });
      } else {
        tokens.push({ type: "string", value: match[1] });
      }
    } else if (match[3] !== undefined) {
      tokens.push({ type: "number", value: match[3] });
    } else if (match[4] !== undefined) {
      tokens.push({ type: "boolean", value: match[4] });
    } else if (match[5] !== undefined) {
      tokens.push({ type: "null", value: match[5] });
    } else if (match[6] !== undefined) {
      tokens.push({ type: "punct", value: match[6] });
    } else if (match[7] !== undefined) {
      // Whitespace — treat as punctuation (no color)
      tokens.push({ type: "punct", value: match[7] });
    }
  }

  // Trailing unmatched text
  if (lastIndex < line.length) {
    tokens.push({ type: "punct", value: line.slice(lastIndex) });
  }

  return tokens;
}

// CSS classes for token types — uses debug theme custom properties
const TOKEN_CLASS: Record<TokenType, string> = {
  key: "text-purple-400",
  string: "text-green-400",
  number: "text-blue-400",
  boolean: "text-yellow-400",
  null: "text-red-400",
  punct: "text-gray-400",
};

// ---------------------------------------------------------------------------
// JsonView component
// ---------------------------------------------------------------------------

interface JsonViewProps {
  /** JSON-serializable data to display. */
  data?: unknown;
  /** Raw JSON string (alternative to data). */
  raw?: string;
  /** Show line numbers. */
  lineNumbers?: boolean;
  /** Max height CSS value. Default: "16rem". */
  maxHeight?: string;
  /** Collapse large output (show first/last lines). Threshold in lines. */
  collapseAfter?: number;
}

const COLLAPSE_THRESHOLD = 30;

export function JsonView({
  data,
  raw,
  lineNumbers = false,
  maxHeight = "16rem",
  collapseAfter,
}: JsonViewProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const text = useMemo(() => {
    if (raw !== undefined) return raw;
    if (data === undefined) return "";
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data, raw]);

  const lines = useMemo(() => text.split("\n"), [text]);
  const threshold = collapseAfter ?? COLLAPSE_THRESHOLD;
  const shouldCollapse = lines.length > threshold && !expanded;

  const displayLines = useMemo(() => {
    if (!shouldCollapse) return lines;
    // Show first 5 + "..." + last 3
    return [
      ...lines.slice(0, 5),
      `  ... ${lines.length - 8} more lines ...`,
      ...lines.slice(-3),
    ];
  }, [lines, shouldCollapse]);

  const tokenizedLines = useMemo(
    () => displayLines.map((line) => tokenizeLine(line)),
    [displayLines],
  );

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [text]);

  if (!text) {
    return <span className="text-[10px] text-gray-400 italic">Empty</span>;
  }

  return (
    <div className="relative group rounded overflow-hidden" style={{ fontFamily: "var(--debug-font-mono, monospace)" }}>
      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="absolute top-1 right-1 z-10 text-[9px] px-1.5 py-0.5 rounded border opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 text-gray-500 hover:text-gray-700 border-gray-200"
      >
        {copied ? "Copied" : "Copy"}
      </button>

      <pre
        className="text-[10px] leading-relaxed overflow-auto select-text"
        style={{ maxHeight }}
      >
        <code>
          {tokenizedLines.map((tokens, lineIdx) => (
            <div key={lineIdx} className="flex">
              {lineNumbers && (
                <span className="select-none text-gray-500 text-right pr-3 w-8 shrink-0 opacity-50">
                  {shouldCollapse && lineIdx >= 5 && lineIdx < displayLines.length - 3
                    ? ""
                    : shouldCollapse && lineIdx >= displayLines.length - 3
                      ? lines.length - (displayLines.length - 1 - lineIdx)
                      : lineIdx + 1}
                </span>
              )}
              <span className="flex-1 whitespace-pre-wrap break-all">
                {tokens.map((tok, i) => (
                  <span key={i} className={TOKEN_CLASS[tok.type]}>{tok.value}</span>
                ))}
              </span>
            </div>
          ))}
        </code>
      </pre>

      {/* Expand/collapse toggle */}
      {lines.length > threshold && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-center text-[10px] py-1 text-gray-400 hover:text-gray-600 border-t bg-gray-50/80"
        >
          {expanded ? `Collapse (${lines.length} lines)` : `Show all ${lines.length} lines`}
        </button>
      )}
    </div>
  );
}
