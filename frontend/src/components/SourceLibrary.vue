<script setup>
defineProps({
  sources: { type: Array, default: () => [] },
  sourceDetail: { type: Object, default: null },
  sourceVersions: { type: Array, default: () => [] },
  sourceVersionDetail: { type: Object, default: null },
  knowledge: { type: Array, default: () => [] },
  knowledgeDetail: { type: Object, default: null }
});

const emit = defineEmits([
  "select-source",
  "select-version",
  "select-knowledge"
]);

/**
 * @param {unknown} value
 * @returns {string}
 */
function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}
</script>

<template>
  <section class="dual-grid">
    <article class="glass-card library-column">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Sources</p>
          <h3>资料库</h3>
        </div>
      </div>

      <div class="list-stack">
        <button
          v-for="item in sources"
          :key="item.id"
          class="list-card"
          @click="emit('select-source', item.id)"
        >
          <strong>{{ item.title || item.canonical_uri || item.id }}</strong>
          <span>{{ item.source_type }} · {{ item.mime_type || "unknown" }}</span>
        </button>
      </div>

      <div v-if="sourceDetail" class="detail-pane">
        <h4>{{ sourceDetail.title || sourceDetail.id }}</h4>
        <pre>{{ prettyJson(sourceDetail) }}</pre>

        <div class="mini-section">
          <h5>Versions</h5>
          <div class="list-stack compact">
            <button
              v-for="version in sourceVersions"
              :key="version.id"
              class="list-card"
              @click="emit('select-version', version.id)"
            >
              <strong>v{{ version.version_no }}</strong>
              <span>{{ version.capture_method }}</span>
            </button>
          </div>
        </div>

        <div v-if="sourceVersionDetail" class="mini-section">
          <h5>Version Detail</h5>
          <pre>{{ prettyJson(sourceVersionDetail) }}</pre>
        </div>
      </div>
    </article>

    <article class="glass-card library-column">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Knowledge</p>
          <h3>知识对象</h3>
        </div>
      </div>

      <div class="list-stack">
        <button
          v-for="item in knowledge"
          :key="item.id"
          class="list-card"
          @click="emit('select-knowledge', item.id)"
        >
          <strong>{{ item.title }}</strong>
          <span>{{ item.knowledge_type }} · {{ item.slug }}</span>
        </button>
      </div>

      <div v-if="knowledgeDetail" class="detail-pane">
        <h4>{{ knowledgeDetail.title }}</h4>
        <pre>{{ prettyJson(knowledgeDetail) }}</pre>
      </div>
    </article>
  </section>
</template>
