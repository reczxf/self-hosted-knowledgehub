<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const items = [
  { label: "Chat", to: "/chat", hint: "主对话台" },
  { label: "Library", to: "/library", hint: "Sources / Knowledge" },
  { label: "Operations", to: "/operations", hint: "Jobs / Events / Search" },
  { label: "Import", to: "/import", hint: "结构化导入 / 上传" }
];

const activePath = computed(() => route.path);
</script>

<template>
  <aside class="app-sidebar">
    <div class="brand-block">
      <p class="eyebrow">PKOS Studio</p>
      <h1>Personal Knowledge OS</h1>
      <p class="brand-copy">
        一个面向 Source、Knowledge 和 Conversation 的内置工作台。
      </p>
    </div>

    <nav class="nav-stack">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: activePath === item.to }"
      >
        <span>{{ item.label }}</span>
        <small>{{ item.hint }}</small>
      </RouterLink>
    </nav>

    <div class="sidebar-card">
      <p class="eyebrow">Built-In UI</p>
      <p>保留内置入口，同时用完整工程结构承载后续演进。</p>
    </div>
  </aside>
</template>
