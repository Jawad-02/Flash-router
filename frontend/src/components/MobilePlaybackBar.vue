<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  frameIndex: number
  totalFrames: number
  phase: string
  isPlaying: boolean
}>()

const emit = defineEmits<{
  play: []
  pause: []
  stepFwd: []
  stepBack: []
}>()

const phaseLabel = computed(() => {
  switch (props.phase) {
    case 'explored': return 'Exploring'
    case 'path': return 'Path'
    case 'done': return 'Done'
    default: return ''
  }
})
</script>

<template>
  <div
    v-if="phase !== 'idle'"
    class="block sm:hidden fixed bottom-0 left-0 right-0 z-[2000] border-t border-border bg-surface-panel/95 px-3 py-2 shadow-lg backdrop-blur-md"
  >
    <div class="mb-1.5 h-1 w-full overflow-hidden rounded-full bg-surface-hover">
      <div
        class="h-full rounded-full transition-all duration-150"
        :class="phase === 'done' ? 'bg-settled' : 'bg-path'"
        :style="{ width: (totalFrames > 0 ? (frameIndex / totalFrames * 100) : 0) + '%' }"
      />
    </div>
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="frameIndex === 0"
          @click="emit('stepBack')"
        >⏮</button>
        <button
          v-if="isPlaying"
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover"
          @click="emit('pause')"
        >⏸</button>
        <button
          v-else
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="phase !== 'explored'"
          @click="emit('play')"
        >▶️</button>
        <button
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="phase !== 'explored' || frameIndex >= totalFrames"
          @click="emit('stepFwd')"
        >⏭</button>
      </div>
      <div class="flex items-center gap-2 font-mono text-[10px] text-text-secondary">
        <span v-if="phaseLabel" class="text-text-secondary/70">{{ phaseLabel }}</span>
        <span>{{ frameIndex }}/{{ totalFrames }}</span>
      </div>
    </div>
  </div>
</template>
