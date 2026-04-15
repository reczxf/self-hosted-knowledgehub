<script setup>
defineProps({
  answer: {
    type: Object,
    default: null
  }
});

/**
 * @param {unknown} value
 * @returns {string}
 */
function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}
</script>

<template>
  <section class="inspector-grid" v-if="answer">
    <article class="glass-card inspector-card">
      <p class="eyebrow">Answer</p>
      <h3>最终回答</h3>
      <pre>{{ answer.answer }}</pre>
      <div class="tag-row">
        <span class="tag-pill">session={{ answer.session_id }}</span>
        <span class="tag-pill">provider={{ answer.provider }}</span>
        <span class="tag-pill">model={{ answer.model }}</span>
        <span class="tag-pill">fallback={{ answer.used_fallback }}</span>
      </div>
    </article>

    <article class="glass-card inspector-card">
      <p class="eyebrow">Knowledge</p>
      <h3>命中知识对象</h3>
      <pre>{{ prettyJson(answer.knowledge_items) }}</pre>
    </article>

    <article class="glass-card inspector-card">
      <p class="eyebrow">Evidence</p>
      <h3>命中原始证据</h3>
      <pre>{{ prettyJson(answer.evidence_items) }}</pre>
    </article>
  </section>
</template>
