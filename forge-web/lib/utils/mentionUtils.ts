/**
 * Utilities for @-mention detection in textarea input.
 *
 * Rules (per D-093):
 * - @ must be preceded by whitespace, newline, or be at position 0
 * - Partial match: only [a-z0-9-] characters after @
 * - Does NOT trigger on email addresses, URLs, or mid-word @
 */

export interface MentionMatch {
  filter: string;
  startIndex: number;
}

/**
 * Extract an active @-mention at the cursor position.
 * Returns the partial filter text and the index of the '@' character,
 * or null if no valid mention is being typed.
 */
export function extractMentionAtCursor(
  text: string,
  cursorPos: number,
): MentionMatch | null {
  // Work backwards from cursor to find @
  const before = text.slice(0, cursorPos);

  // Find the last @ before cursor
  const atIndex = before.lastIndexOf("@");
  if (atIndex === -1) return null;

  // Rule: @ must be at position 0 or preceded by whitespace
  if (atIndex > 0) {
    const charBefore = before[atIndex - 1];
    if (!/\s/.test(charBefore)) return null;
  }

  // Extract the part after @ up to cursor
  const partial = before.slice(atIndex + 1);

  // Rule: only [a-z0-9-] allowed in mention
  if (!/^[a-z0-9-]*$/.test(partial)) return null;

  return { filter: partial, startIndex: atIndex };
}

/**
 * Get caret pixel coordinates relative to a textarea element.
 * Uses the mirror element technique to measure text position.
 */
export function getCaretCoordinates(
  textarea: HTMLTextAreaElement,
  position: number,
): { top: number; left: number } {
  const mirror = document.createElement("div");
  const style = getComputedStyle(textarea);

  // Copy relevant styles
  const props = [
    "fontFamily", "fontSize", "fontWeight", "fontStyle",
    "letterSpacing", "lineHeight", "padding", "paddingTop",
    "paddingRight", "paddingBottom", "paddingLeft",
    "borderWidth", "boxSizing", "whiteSpace", "wordWrap",
    "wordBreak", "overflowWrap",
  ] as const;

  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.overflow = "hidden";
  mirror.style.width = `${textarea.offsetWidth}px`;

  for (const prop of props) {
    (mirror.style as Record<string, string>)[prop] = style.getPropertyValue(
      prop.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`),
    );
  }
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.wordWrap = "break-word";

  // Insert text up to position, then add a span marker
  const textBefore = textarea.value.slice(0, position);
  const textNode = document.createTextNode(textBefore);
  const marker = document.createElement("span");
  marker.textContent = "\u200b"; // zero-width space

  mirror.appendChild(textNode);
  mirror.appendChild(marker);
  document.body.appendChild(mirror);

  const markerRect = marker.offsetLeft;
  const markerTop = marker.offsetTop;

  document.body.removeChild(mirror);

  return {
    top: markerTop - textarea.scrollTop,
    left: markerRect,
  };
}
