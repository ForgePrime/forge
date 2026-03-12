"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";

interface LeftPanelContextValue {
  content: ReactNode | null;
  setContent: (node: ReactNode | null) => void;
}

const LeftPanelContext = createContext<LeftPanelContextValue>({
  content: null,
  setContent: () => {},
});

export function LeftPanelProvider({ children }: { children: ReactNode }) {
  const [content, setContent] = useState<ReactNode | null>(null);
  return (
    <LeftPanelContext.Provider value={{ content, setContent }}>
      {children}
    </LeftPanelContext.Provider>
  );
}

/**
 * Hook for pages to declare left panel content.
 * Content is set on mount and cleared on unmount.
 */
export function useLeftPanel(content: ReactNode) {
  const { setContent } = useContext(LeftPanelContext);

  useEffect(() => {
    setContent(content);
    return () => setContent(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setContent]);
}

/**
 * Hook for the layout to read current left panel content.
 */
export function useLeftPanelContent() {
  return useContext(LeftPanelContext).content;
}
