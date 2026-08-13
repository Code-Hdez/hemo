import type { ChatScope } from "./types";

const LEGACY_PREFIX = "hemovet4-chat:v1:";
const REGISTRY_PREFIX = "hemovet4-chat:v2:";
const BROWSER_SESSION_KEY = "hemovet4-chat:browser-session:v1";
const MAX_CONTEXTS_PER_USER = 24;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
let pageBrowserSessionId: string | undefined;

export function browserChatSessionId(): string {
  if (pageBrowserSessionId) return pageBrowserSessionId;
  try {
    const existing = sessionStorage.getItem(BROWSER_SESSION_KEY);
    if (existing && UUID_PATTERN.test(existing)) {
      pageBrowserSessionId = existing;
      return existing;
    }
    const created = crypto.randomUUID();
    sessionStorage.setItem(BROWSER_SESSION_KEY, created);
    pageBrowserSessionId = created;
    return created;
  } catch {
    // Hardened browsers may disable sessionStorage. A fresh per-page value is
    // still safer than falling back to a long-lived localStorage identifier.
    pageBrowserSessionId = crypto.randomUUID();
    return pageBrowserSessionId;
  }
}

export interface ChatSessionManifest {
  version: 2;
  userId: string;
  conversationId: string;
  contextRevision: number;
  scope: ChatScope;
  contextKey: string;
  petId?: string;
  analysisId?: string;
  lastClientMessageId?: string;
  updatedAt: string;
}

export interface ChatSessionRegistry {
  version: 2;
  userId: string;
  activeContextKey?: string;
  contexts: Record<string, ChatSessionManifest>;
  updatedAt: string;
}

interface LegacyChatSessionManifest {
  version: 1;
  userId: string;
  conversationId: string;
  contextRevision: number;
  scope: ChatScope;
  contextKey: string;
  petId?: string;
  analysisId?: string;
  lastClientMessageId?: string;
  updatedAt: string;
}

function registryKey(userId: string): string {
  return `${REGISTRY_PREFIX}${userId}`;
}

function legacyKey(userId: string): string {
  return `${LEGACY_PREFIX}${userId}`;
}

function isScope(value: unknown): value is ChatScope {
  return ["general", "selected_hemogram", "hemogram_history"].includes(String(value));
}

function validIsoDate(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function validManifest(
  value: unknown,
  userId: string,
  expectedContextKey?: string,
): value is ChatSessionManifest {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<ChatSessionManifest>;
  return (
    candidate.version === 2 &&
    candidate.userId === userId &&
    typeof candidate.conversationId === "string" &&
    candidate.conversationId.length > 0 &&
    typeof candidate.contextRevision === "number" &&
    Number.isInteger(candidate.contextRevision) &&
    candidate.contextRevision > 0 &&
    isScope(candidate.scope) &&
    typeof candidate.contextKey === "string" &&
    candidate.contextKey.length > 0 &&
    (!expectedContextKey || candidate.contextKey === expectedContextKey) &&
    validIsoDate(candidate.updatedAt)
  );
}

function validLegacyManifest(value: unknown, userId: string): value is LegacyChatSessionManifest {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<LegacyChatSessionManifest>;
  return (
    candidate.version === 1 &&
    candidate.userId === userId &&
    typeof candidate.conversationId === "string" &&
    candidate.conversationId.length > 0 &&
    typeof candidate.contextRevision === "number" &&
    Number.isInteger(candidate.contextRevision) &&
    candidate.contextRevision > 0 &&
    isScope(candidate.scope) &&
    typeof candidate.contextKey === "string" &&
    candidate.contextKey.length > 0 &&
    validIsoDate(candidate.updatedAt)
  );
}

function projectManifest(
  value: unknown,
  userId: string,
  expectedContextKey?: string,
): ChatSessionManifest | undefined {
  if (!validManifest(value, userId, expectedContextKey)) return undefined;
  const candidate = value as ChatSessionManifest;
  return {
    version: 2,
    userId,
    conversationId: candidate.conversationId,
    contextRevision: candidate.contextRevision,
    scope: candidate.scope,
    contextKey: candidate.contextKey,
    ...(typeof candidate.petId === "string" ? { petId: candidate.petId } : {}),
    ...(typeof candidate.analysisId === "string" ? { analysisId: candidate.analysisId } : {}),
    ...(typeof candidate.lastClientMessageId === "string"
      ? { lastClientMessageId: candidate.lastClientMessageId }
      : {}),
    updatedAt: candidate.updatedAt,
  };
}

function emptyRegistry(userId: string): ChatSessionRegistry {
  return {
    version: 2,
    userId,
    contexts: {},
    updatedAt: new Date().toISOString(),
  };
}

function persistRegistry(registry: ChatSessionRegistry): void {
  sessionStorage.setItem(registryKey(registry.userId), JSON.stringify(registry));
}

function migrateLegacyRegistry(userId: string): ChatSessionRegistry | undefined {
  const raw = sessionStorage.getItem(legacyKey(userId));
  if (!raw) return undefined;
  sessionStorage.removeItem(legacyKey(userId));
  try {
    const legacy = JSON.parse(raw) as unknown;
    if (!validLegacyManifest(legacy, userId)) return undefined;
    const manifest: ChatSessionManifest = {
      version: 2,
      userId,
      conversationId: legacy.conversationId,
      contextRevision: legacy.contextRevision,
      scope: legacy.scope,
      contextKey: legacy.contextKey,
      ...(typeof legacy.petId === "string" ? { petId: legacy.petId } : {}),
      ...(typeof legacy.analysisId === "string" ? { analysisId: legacy.analysisId } : {}),
      ...(typeof legacy.lastClientMessageId === "string"
        ? { lastClientMessageId: legacy.lastClientMessageId }
        : {}),
      updatedAt: legacy.updatedAt,
    };
    const registry: ChatSessionRegistry = {
      version: 2,
      userId,
      activeContextKey: manifest.contextKey,
      contexts: { [manifest.contextKey]: manifest },
      updatedAt: manifest.updatedAt,
    };
    persistRegistry(registry);
    return registry;
  } catch {
    return undefined;
  }
}

export function loadChatSessionRegistry(userId: string): ChatSessionRegistry {
  try {
    const raw = sessionStorage.getItem(registryKey(userId));
    if (!raw) return migrateLegacyRegistry(userId) ?? emptyRegistry(userId);
    const parsed = JSON.parse(raw) as Partial<ChatSessionRegistry>;
    if (
      parsed.version !== 2 ||
      parsed.userId !== userId ||
      typeof parsed.contexts !== "object" ||
      parsed.contexts === null
    ) {
      sessionStorage.removeItem(registryKey(userId));
      return migrateLegacyRegistry(userId) ?? emptyRegistry(userId);
    }

    const contexts = Object.fromEntries(
      Object.entries(parsed.contexts).flatMap(([contextKey, value]) => {
        const manifest = projectManifest(value, userId, contextKey);
        return manifest ? [[contextKey, manifest]] : [];
      }),
    ) as Record<string, ChatSessionManifest>;
    const activeContextKey =
      typeof parsed.activeContextKey === "string" && contexts[parsed.activeContextKey]
        ? parsed.activeContextKey
        : undefined;
    const registry: ChatSessionRegistry = {
      version: 2,
      userId,
      activeContextKey,
      contexts,
      updatedAt: validIsoDate(parsed.updatedAt) ? parsed.updatedAt : new Date().toISOString(),
    };
    if (
      Object.keys(contexts).length !== Object.keys(parsed.contexts).length ||
      JSON.stringify(contexts) !== JSON.stringify(parsed.contexts)
    ) {
      persistRegistry(registry);
    }
    return registry;
  } catch {
    try {
      sessionStorage.removeItem(registryKey(userId));
    } catch {
      // Storage is optional; the backend remains the source of truth.
    }
    return emptyRegistry(userId);
  }
}

export function loadChatSessionManifest(
  userId: string,
  contextKey?: string,
): ChatSessionManifest | undefined {
  const registry = loadChatSessionRegistry(userId);
  const selectedKey = contextKey ?? registry.activeContextKey;
  return selectedKey ? registry.contexts[selectedKey] : undefined;
}

export function saveChatSessionManifest(manifest: ChatSessionManifest): void {
  try {
    const registry = loadChatSessionRegistry(manifest.userId);
    const contexts = { ...registry.contexts, [manifest.contextKey]: manifest };
    const retained = Object.values(contexts)
      .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
      .slice(0, MAX_CONTEXTS_PER_USER);
    const nextContexts = Object.fromEntries(
      retained.map((entry) => [entry.contextKey, entry]),
    ) as Record<string, ChatSessionManifest>;
    persistRegistry({
      version: 2,
      userId: manifest.userId,
      activeContextKey: manifest.contextKey,
      contexts: nextContexts,
      updatedAt: manifest.updatedAt,
    });
    sessionStorage.removeItem(legacyKey(manifest.userId));
  } catch {
    // Storage can be unavailable in hardened/private browsing contexts. The
    // authorized backend transcript remains the source of truth.
  }
}

export function clearChatSessionManifest(userId: string, contextKey?: string): void {
  try {
    if (!contextKey) {
      sessionStorage.removeItem(registryKey(userId));
      sessionStorage.removeItem(legacyKey(userId));
      return;
    }
    const registry = loadChatSessionRegistry(userId);
    const contexts = { ...registry.contexts };
    delete contexts[contextKey];
    if (Object.keys(contexts).length === 0) {
      sessionStorage.removeItem(registryKey(userId));
      return;
    }
    const activeContextKey =
      registry.activeContextKey === contextKey ? undefined : registry.activeContextKey;
    persistRegistry({
      ...registry,
      activeContextKey,
      contexts,
      updatedAt: new Date().toISOString(),
    });
  } catch {
    // No-op when storage is unavailable.
  }
}

export function clearAllChatSessionManifests(): void {
  pageBrowserSessionId = undefined;
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const storageKey = sessionStorage.key(index);
      if (storageKey?.startsWith(REGISTRY_PREFIX) || storageKey?.startsWith(LEGACY_PREFIX)) {
        sessionStorage.removeItem(storageKey);
      }
    }
    sessionStorage.removeItem(BROWSER_SESSION_KEY);
  } catch {
    // No-op when storage is unavailable.
  }
}
