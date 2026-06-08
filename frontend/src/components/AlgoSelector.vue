<script setup lang="ts">
defineProps<{
  algorithm: string
  disabled: boolean
}>()

const emit = defineEmits<{
  'update:algorithm': [value: string]
}>()

const algos: { key: string; label: string }[] = [
  { key: '', label: 'Dijkstra' },
  { key: 'astar', label: 'A*' },
  { key: 'bidirectional', label: 'Bi-D' },
  { key: 'greedy', label: 'Greedy' },
]
</script>

<template>
  <div class="flex items-center gap-0.5 rounded-lg bg-surface-hover p-0.5">
    <button
      v-for="a in algos"
      :key="a.key"
      :disabled="disabled"
      class="rounded-md px-1.5 sm:px-2 py-1 text-[10px] sm:text-[11px] font-medium transition-all duration-150"
      :class="algorithm === a.key
        ? 'bg-surface-panel text-text-primary shadow-sm'
        : 'text-text-secondary hover:text-text-primary'"
      @click="emit('update:algorithm', a.key)"
    >
      {{ a.label }}
    </button>
  </div>
</template>
