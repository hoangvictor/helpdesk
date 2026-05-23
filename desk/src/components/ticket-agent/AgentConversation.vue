<!--
  Place this file at:  desk/src/components/ticket-agent/AgentConversation.vue

  Renders the conversation between the end-user and your custom agent for the
  current ticket. It reads `conversation_id` from the injected ticket and calls
  the server-side proxy (helpdesk.api.agent_conversation.get_messages), which
  in turn calls your agent's /v1/messages endpoint with the Bearer key.
-->
<template>
  <div class="flex flex-col flex-1 overflow-y-auto px-5 py-4">
    <!-- Loading -->
    <div
      v-if="conversation.loading"
      class="flex flex-1 items-center justify-center flex-col gap-2"
    >
      <Button :loading="true" variant="ghost" size="2xl" />
      <p class="text-base text-ink-gray-5">{{ __("Loading conversation…") }}</p>
    </div>

    <!-- Error -->
    <div
      v-else-if="conversation.error"
      class="flex flex-1 items-center justify-center"
    >
      <p class="text-base text-ink-red-4">
        {{ conversation.error.messages?.[0] || __("Failed to load conversation.") }}
      </p>
    </div>

    <!-- No conversation_id on the ticket -->
    <div
      v-else-if="!conversationId"
      class="flex flex-1 items-center justify-center"
    >
      <p class="text-base text-ink-gray-5">
        {{ __("This ticket has no linked agent conversation.") }}
      </p>
    </div>

    <!-- Empty -->
    <div
      v-else-if="messages.length === 0"
      class="flex flex-1 items-center justify-center"
    >
      <p class="text-base text-ink-gray-5">{{ __("No messages yet.") }}</p>
    </div>

    <!-- Messages -->
    <div v-else class="flex flex-col gap-4">
      <div
        v-for="(msg, idx) in messages"
        :key="msg.id || idx"
        class="flex gap-3"
        :class="msg.role === 'assistant' ? 'flex-row' : 'flex-row-reverse'"
      >
        <Avatar
          :label="msg.role === 'assistant' ? 'Agent' : 'User'"
          size="md"
          class="flex-shrink-0"
        />
        <div
          class="rounded-lg border border-outline-gray-2 px-4 py-2.5 max-w-[75%]"
          :class="
            msg.role === 'assistant'
              ? 'bg-surface-white'
              : 'bg-surface-gray-2'
          "
        >
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-medium text-ink-gray-7">
              {{ msg.role === "assistant" ? __("Agent") : __("User") }}
            </span>
            <span v-if="msg.timestamp" class="text-xs text-ink-gray-5">
              {{ formatTime(msg.timestamp) }}
            </span>
          </div>
          <p class="text-p-sm text-ink-gray-8 whitespace-pre-wrap">
            {{ msg.content }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TicketSymbol } from "@/types";
import { Avatar, Button, createResource, dayjs } from "frappe-ui";
import { computed, inject } from "vue";

const ticket = inject(TicketSymbol)!;

const conversationId = computed(() => ticket.value?.doc?.conversation_id);
const userId = computed(() => ticket.value?.doc?.user_id);

const conversation = createResource({
  url: "helpdesk.api.agent_conversation.get_messages",
  makeParams: () => ({
    conversation_id: conversationId.value,
    user_id: userId.value,
  }),
  // Only fire when there is actually a conversation_id to fetch.
  auto: Boolean(conversationId.value),
});

/**
 * Dify's GET /v1/messages returns Q&A PAIRS, not single messages. Each item
 * looks like:
 *   { id, conversation_id, query: "<user text>", answer: "<agent text>",
 *     created_at: <unix seconds>, ... }
 *
 * So every item must be split into TWO bubbles: the user's query, then the
 * agent's answer. We also flatten the wrapper: createResource already strips
 * Frappe's outer `message`, so conversation.data is { data: [...], has_more },
 * and the array we want is conversation.data.data.
 */
const messages = computed(() => {
  const payload = conversation.data;
  if (!payload) return [];

  // The proxy/Dify array: try the nested `data`, then common fallbacks.
  const raw =
    payload.data ||
    payload.messages ||
    (Array.isArray(payload) && payload) ||
    [];

  const out: {
    id: string | number;
    role: "user" | "assistant";
    content: string;
    timestamp: number | string | null;
  }[] = [];

  raw.forEach((m: any, i: number) => {
    const ts = m.created_at ?? m.timestamp ?? m.creation ?? null;

    // user side
    if (m.query) {
      out.push({
        id: `${m.id ?? i}-q`,
        role: "user",
        content: m.query,
        timestamp: ts,
      });
    }
    // agent side
    if (m.answer) {
      out.push({
        id: `${m.id ?? i}-a`,
        role: "assistant",
        content: m.answer,
        timestamp: ts,
      });
    }
  });

  return out;
});

function formatTime(ts: number | string) {
  // Dify sends unix SECONDS; dayjs expects ms. Multiply if it's a number.
  const value = typeof ts === "number" ? ts * 1000 : ts;
  return dayjs(value).format("DD MMM, h:mm a");
}
</script>