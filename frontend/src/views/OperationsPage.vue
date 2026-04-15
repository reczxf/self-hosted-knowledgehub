<script setup>
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import OperationsBoard from "../components/OperationsBoard.vue";
import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const { jobs, events, searchResults, busy } = storeToRefs(workspaceStore);

onMounted(async () => {
  await Promise.all([workspaceStore.loadJobs(), workspaceStore.loadEvents()]);
});
</script>

<template>
  <section class="page-stack">
    <div class="hero-panel compact">
      <p class="eyebrow">Operations</p>
      <h2>把异步任务、事件流和检索能力收拢到一个操作面板。</h2>
    </div>

    <OperationsBoard
      :jobs="jobs"
      :events="events"
      :search-mode="workspaceStore.searchMode"
      :search-query="workspaceStore.searchQuery"
      :search-results="searchResults"
      :busy="busy"
      @run-jobs="workspaceStore.runJobs"
      @update:search-mode="workspaceStore.searchMode = $event"
      @update:search-query="workspaceStore.searchQuery = $event"
      @search="workspaceStore.runSearch"
    />
  </section>
</template>
