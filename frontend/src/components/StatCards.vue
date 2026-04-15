<script setup>
defineProps({
  stats: {
    type: Object,
    required: true
  }
});

const cards = [
  { key: "sources", label: "Sources" },
  { key: "knowledge", label: "Knowledge" },
  { key: "events", label: "Events" },
  { key: "jobs", label: "Jobs" }
];
</script>

<template>
  <section class="stat-grid">
    <article v-for="card in cards" :key="card.key" class="glass-card stat-card">
      <p class="eyebrow">{{ card.label }}</p>
      <strong>{{ stats[card.key] ?? 0 }}</strong>
    </article>
  </section>
</template>
