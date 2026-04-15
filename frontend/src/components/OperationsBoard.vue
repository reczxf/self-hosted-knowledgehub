<script setup>
defineProps({
  jobs: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
  searchMode: { type: String, default: "text" },
  searchQuery: { type: String, default: "" },
  searchResults: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false }
});

const emit = defineEmits([
  "run-jobs",
  "update:searchMode",
  "update:searchQuery",
  "search"
]);

/**
 * @param {Event} event
 * @returns {void}
 */
function onSearchModeChange(event) {
  emit("update:searchMode", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onSearchQueryInput(event) {
  emit("update:searchQuery", event.target.value);
}
</script>

<template>
  <section class="operations-grid">
    <article class="glass-card operations-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Jobs</p>
          <h3>处理队列</h3>
        </div>
        <button class="primary-button" :disabled="busy" @click="emit('run-jobs')">
          执行待处理任务
        </button>
      </div>

      <div class="list-stack compact">
        <div v-for="job in jobs" :key="job.id" class="list-card static">
          <strong>{{ job.job_type }}</strong>
          <span>{{ job.status }} · attempts={{ job.attempts }}</span>
        </div>
      </div>
    </article>

    <article class="glass-card operations-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Events</p>
          <h3>最近事件</h3>
        </div>
      </div>
      <div class="list-stack compact">
        <div v-for="event in events" :key="event.id" class="list-card static">
          <strong>{{ event.event_type }}</strong>
          <span>{{ event.occurred_at }}</span>
        </div>
      </div>
    </article>

    <article class="glass-card operations-card wide">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Search</p>
          <h3>全文 / 语义检索</h3>
        </div>
      </div>

      <div class="composer-tools">
        <select :value="searchMode" @change="onSearchModeChange">
          <option value="text">全文检索</option>
          <option value="semantic">语义检索</option>
        </select>
        <input
          :value="searchQuery"
          placeholder="输入检索词"
          @input="onSearchQueryInput"
        />
        <button class="primary-button" :disabled="busy" @click="emit('search')">
          搜索
        </button>
      </div>

      <div class="list-stack">
        <div
          v-for="item in searchResults"
          :key="item.document.id"
          class="list-card static"
        >
          <strong>{{ item.document.title || item.document.id }}</strong>
          <span>{{ item.match_type }} · score={{ item.score }}</span>
          <p>{{ item.document.plain_text_preview }}</p>
        </div>
      </div>
    </article>
  </section>
</template>
