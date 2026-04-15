<script setup>
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import SourceLibrary from "../components/SourceLibrary.vue";
import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const {
  sources,
  sourceDetail,
  sourceVersions,
  sourceVersionDetail,
  knowledge,
  knowledgeDetail
} = storeToRefs(workspaceStore);

onMounted(async () => {
  if (!workspaceStore.sources.length || !workspaceStore.knowledge.length) {
    await Promise.all([workspaceStore.loadSources(), workspaceStore.loadKnowledge()]);
  }
});
</script>

<template>
  <section class="page-stack">
    <div class="hero-panel compact">
      <p class="eyebrow">Library</p>
      <h2>把 Source 和 Knowledge 当成可检视的资产，而不是后台数据。</h2>
    </div>

    <SourceLibrary
      :sources="sources"
      :source-detail="sourceDetail"
      :source-versions="sourceVersions"
      :source-version-detail="sourceVersionDetail"
      :knowledge="knowledge"
      :knowledge-detail="knowledgeDetail"
      @select-source="workspaceStore.selectSource"
      @select-version="workspaceStore.selectSourceVersion"
      @select-knowledge="workspaceStore.selectKnowledge"
    />
  </section>
</template>
