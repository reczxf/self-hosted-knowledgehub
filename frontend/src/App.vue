<script setup>
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import AppSidebar from "./components/AppSidebar.vue";
import TopStatusBar from "./components/TopStatusBar.vue";
import { useWorkspaceStore } from "./stores/workspace";

const workspaceStore = useWorkspaceStore();
const { busy, message, messageType } = storeToRefs(workspaceStore);

onMounted(async () => {
  try {
    await workspaceStore.bootstrap();
  } catch (error) {
    workspaceStore.setMessage(`初始化失败：${error.message}`, "error");
  }
});
</script>

<template>
  <div class="app-shell">
    <div class="background-orb orb-left"></div>
    <div class="background-orb orb-right"></div>

    <AppSidebar />

    <main class="app-main">
      <TopStatusBar
        :busy="busy"
        :message="message"
        :message-type="messageType"
      />

      <RouterView />
    </main>
  </div>
</template>
