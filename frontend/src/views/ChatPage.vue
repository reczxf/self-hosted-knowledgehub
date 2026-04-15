<script setup>
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import AnswerInspector from "../components/AnswerInspector.vue";
import ChatComposer from "../components/ChatComposer.vue";
import ChatTranscript from "../components/ChatTranscript.vue";
import StatCards from "../components/StatCards.vue";
import { useConversationStore } from "../stores/conversation";
import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const conversationStore = useConversationStore();

const { stats } = storeToRefs(workspaceStore);
const { answer, turns, busy } = storeToRefs(conversationStore);

/**
 * @returns {Promise<void>}
 */
async function submitConversation() {
  if (!conversationStore.question.trim()) {
    workspaceStore.setMessage("请输入问题。", "error");
    return;
  }

  try {
    const response = await conversationStore.ask();
    workspaceStore.setMessage(`已生成结构化回答，会话=${response.session_id}`);
  } catch (error) {
    workspaceStore.setMessage(`对话失败：${error.message}`, "error");
  }
}

onMounted(async () => {
  if (!workspaceStore.sources.length && !workspaceStore.knowledge.length) {
    await workspaceStore.bootstrap();
  }
});
</script>

<template>
  <section class="page-stack">
    <div class="hero-panel">
      <p class="eyebrow">Chat Workspace</p>
      <h2>一个更接近常规 AI Chat 的 PKOS 主界面。</h2>
      <p>
        对话是主入口，知识命中、原始证据和系统指标作为辅助视图围绕它展开。
      </p>
    </div>

    <StatCards :stats="stats" />

    <div class="chat-layout">
      <div class="chat-column">
        <ChatComposer
          :model-value="conversationStore.question"
          :session-id="conversationStore.sessionId"
          :mode="conversationStore.mode"
          :busy="busy"
          @update:model-value="conversationStore.question = $event"
          @update:session-id="conversationStore.sessionId = $event"
          @update:mode="conversationStore.mode = $event"
          @submit="submitConversation"
          @reset="conversationStore.resetSession()"
        />
        <ChatTranscript :turns="turns" />
      </div>

      <div class="context-column">
        <AnswerInspector :answer="answer" />
      </div>
    </div>
  </section>
</template>
