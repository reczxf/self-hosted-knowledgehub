<script setup>
defineProps({
  busy: { type: Boolean, default: false },
  message: { type: String, default: "" },
  messageType: { type: String, default: "info" }
});
</script>

<template>
  <header class="top-status">
    <div>
      <p class="eyebrow">Workspace</p>
      <h2>Chat-first console with project structure.</h2>
    </div>
    <div class="status-chip-row">
      <span class="status-chip" :class="{ active: busy }">
        {{ busy ? "Working" : "Ready" }}
      </span>
      <span v-if="message" class="status-chip" :class="{ danger: messageType === 'error' }">
        {{ message }}
      </span>
    </div>
  </header>
</template>
