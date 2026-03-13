export { AIPageProvider, useAIPageContext, useAIPageContextSafe } from "./AIPageProvider";
export { useAIPage } from "./useAIPage";
export { useAIElement } from "./useAIElement";
export { serializePageContext } from "./serializer";
export type { SerializeOptions } from "./serializer";
export { deriveScopesFromElements } from "./deriveScopes";
export type {
  AIElementDescriptor,
  AIActionDescriptor,
  AIPageConfig,
  AIContextSnapshot,
} from "./types";
