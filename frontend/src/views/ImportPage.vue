<script setup>
import { storeToRefs } from "pinia";

import ImportWorkbench from "../components/ImportWorkbench.vue";
import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const { busy } = storeToRefs(workspaceStore);
</script>

<template>
  <section class="page-stack">
    <div class="hero-panel compact">
      <p class="eyebrow">Import</p>
      <h2>保留工程化前端，同时不丢掉数据导入这条核心操作链。</h2>
    </div>

    <ImportWorkbench
      :import-kind="workspaceStore.importKind"
      :import-payload="workspaceStore.importPayload"
      :upload-title="workspaceStore.uploadTitle"
      :upload-occurred-at="workspaceStore.uploadOccurredAt"
      :upload-file="workspaceStore.uploadFile"
      :busy="busy"
      @update:import-kind="workspaceStore.setImportKind($event)"
      @update:import-payload="workspaceStore.importPayload = $event"
      @update:upload-title="workspaceStore.uploadTitle = $event"
      @update:upload-occurred-at="workspaceStore.uploadOccurredAt = $event"
      @update:upload-file="workspaceStore.uploadFile = $event"
      @submit-structured="workspaceStore.submitStructuredImport"
      @submit-upload="workspaceStore.submitUpload"
    />
  </section>
</template>
