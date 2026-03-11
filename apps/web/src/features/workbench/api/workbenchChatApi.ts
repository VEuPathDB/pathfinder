import { requestJson } from "@/lib/api/http";
import type { ChatSSEEvent } from "@/features/chat/sse_events";
import type { RawSSEData } from "@/features/chat/sse_events";
import { parseChatSSEEvent } from "@/features/chat/sse_events";
import {
  subscribeToOperation,
  type OperationSubscription,
} from "@/lib/operationSubscribe";

interface WorkbenchChatResponse {
  operationId: string;
  streamId: string;
}

export interface WorkbenchChatMessage {
  role: "user" | "assistant";
  content: string;
  messageId?: string;
  timestamp?: string;
  toolCalls?: unknown[];
  citations?: unknown[];
}

export async function postWorkbenchChat(
  experimentId: string,
  message: string,
  siteId: string,
  options?: { model?: string; signal?: AbortSignal },
): Promise<WorkbenchChatResponse> {
  return requestJson<WorkbenchChatResponse>(
    `/api/v1/experiments/${experimentId}/chat`,
    {
      method: "POST",
      body: { message, siteId, model: options?.model },
      signal: options?.signal,
    },
  );
}

export async function getWorkbenchChatMessages(
  experimentId: string,
): Promise<WorkbenchChatMessage[]> {
  return requestJson<WorkbenchChatMessage[]>(
    `/api/v1/experiments/${experimentId}/chat/messages`,
  );
}

export function streamWorkbenchChat(
  experimentId: string,
  message: string,
  siteId: string,
  callbacks: {
    onMessage: (event: ChatSSEEvent) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
  },
  options?: { model?: string; signal?: AbortSignal },
): {
  promise: Promise<{ operationId: string; streamId: string }>;
  cancel: () => void;
} {
  let subscription: OperationSubscription | null = null;

  const promise = (async () => {
    const { operationId, streamId } = await postWorkbenchChat(
      experimentId,
      message,
      siteId,
      options,
    );

    subscription = subscribeToOperation<RawSSEData>(operationId, {
      onEvent: ({ type, data }) => {
        const parsed = parseChatSSEEvent({ type, data });
        if (parsed) callbacks.onMessage(parsed);
      },
      onError: callbacks.onError,
      onComplete: callbacks.onComplete,
      endEventTypes: new Set(["message_end"]),
    });

    return { operationId, streamId };
  })();

  return {
    promise,
    cancel: () => subscription?.unsubscribe(),
  };
}
