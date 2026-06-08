<script setup lang="ts">
defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <div class="flex items-center gap-2">
    <span
      class="text-xs font-medium select-none"
      :class="modelValue ? 'text-traffic' : 'text-text-secondary'"
    >
      Traffic
    </span>
    <button
      role="switch"
      :aria-checked="modelValue"
      :class="modelValue ? 'bg-traffic' : 'bg-surface-hover'"
      class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full
             transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2
             focus-visible:ring-path focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel"
      @click="emit('update:modelValue', !modelValue)"
    >
      <span
        :class="modelValue ? 'translate-x-[18px]' : 'translate-x-0.5'"
        class="inline-block size-3.5 rounded-full bg-white transition-transform duration-200"
      />
    </button>
  </div>
</template>
