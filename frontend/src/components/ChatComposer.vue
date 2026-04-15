<script setup>
const props = defineProps({
  modelValue: { type: String, default: "" },
  sessionId: { type: String, default: "" },
  mode: { type: String, default: "hybrid" },
  busy: { type: Boolean, default: false }
});

const emit = defineEmits([
  "update:modelValue",
  "update:sessionId",
  "update:mode",
  "submit",
  "reset"
]);

/**
 * @param {Event} event
 * @returns {void}
 */
function onQuestionInput(event) {
  emit("update:modelValue", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onSessionInput(event) {
  emit("update:sessionId", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onModeChange(event) {
  emit("update:mode", event.target.value);
}
</script>

<template>
  <section class="glass-card composer-card">
    <div class="composer-header">
      <div>
        <p class="eyebrow">Conversation</p>
        <h3>像常规 AI Chat 一样连续提问</h3>
      </div>
      <button class="secondary-button" :disabled="busy" @click="emit('reset')">
        新会话
      </button>
    </div>

    <div class="composer-tools">
      <select :value="mode" @change="onModeChange">
        <option value="hybrid">混合召回</option>
        <option value="text">全文优先</option>
        <option value="semantic">语义优先</option>
      </select>
      <input
        :value="sessionId"
        placeholder="可选：输入已有 session_id，或留空自动创建"
        @input="onSessionInput"
      />
    </div>

    <textarea
      :value="modelValue"
      rows="5"
      placeholder="输入你的问题，例如：目前 PKOS 已经具备哪些能力？"
      @input="onQuestionInput"
    />

    <div class="composer-actions">
      <button class="primary-button" :disabled="busy" @click="emit('submit')">
        {{ busy ? "生成中..." : "发送问题" }}
      </button>
    </div>
  </section>
</template>
