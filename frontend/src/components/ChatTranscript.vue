<script setup>
defineProps({
  turns: {
    type: Array,
    default: () => []
  }
});
</script>

<template>
  <section class="glass-card transcript-card">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Transcript</p>
        <h3>当前会话</h3>
      </div>
    </div>

    <div v-if="turns.length" class="bubble-list">
      <article
        v-for="turn in turns"
        :key="turn.id"
        class="message-bubble"
        :class="turn.role === 'assistant' ? 'assistant' : 'user'"
      >
        <div class="bubble-meta">
          <span>{{ turn.role === "assistant" ? "Assistant" : "You" }}</span>
          <small>#{{ turn.turn_no }}</small>
        </div>
        <p>{{ turn.content }}</p>
      </article>
    </div>

    <div v-else class="empty-state">
      还没有会话内容，先发送一个问题。
    </div>
  </section>
</template>
