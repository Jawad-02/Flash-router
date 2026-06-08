<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  algorithm: string
  computationMs: number
  exploredTotal: number
  exploredRendered: number
  pathEdgeCount: number
  routeCost: number | null
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

const algoLabel = computed(() => {
  const map: Record<string, string> = {
    '': 'Dijkstra',
    astar: 'A*',
    bidirectional: 'Bi-Directional',
    greedy: 'Greedy Best-First',
  }
  return map[props.algorithm] || 'Dijkstra'
})

const phaseLabel = computed(() => {
  switch (props.phase) {
    case 'idle': return ''
    case 'explored': return 'Exploring'
    case 'path': return 'Path'
    case 'done': return 'Done'
    default: return ''
  }
})
</script>

<template>
  <div
    class="pointer-events-auto w-40 lg:w-56 rounded-xl
           border border-border bg-surface-panel/90 p-4 shadow-lg backdrop-blur-md hidden sm:block"
  >
    <h2 class="mb-3 text-sm font-semibold text-text-primary">Telemetry</h2>

    <div v-if="routeCost !== null && routeCost >= 0" class="space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Algorithm</span>
        <span class="text-xs font-mono text-frontier">{{ algoLabel }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Computation</span>
        <span class="text-xs font-mono text-frontier">{{ computationMs.toFixed(1) }} ms</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Explored</span>
        <span class="text-xs font-mono text-frontier">{{ exploredTotal.toLocaleString() }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Rendered</span>
        <span class="text-xs font-mono text-frontier">{{ exploredRendered.toLocaleString() }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Path edges</span>
        <span class="text-xs font-mono text-frontier">{{ pathEdgeCount.toLocaleString() }}</span>
      </div>
      <div v-if="routeCost" class="flex items-center justify-between border-t border-border/40 pt-2">
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-secondary">Total cost</span>
        <span class="text-xs font-mono text-settled">{{ routeCost.toFixed(4) }} km</span>
      </div>
    </div>

    <div v-else>
      <p class="text-xs text-text-secondary">No route data yet.</p>
      <p class="mt-1 text-[10px] text-text-secondary leading-tight">Place start and end markers, then click Find Route.</p>
    </div>

    <div v-if="phase !== 'idle'" class="mt-3 border-t border-border/40 pt-3">
      <div class="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <div
          class="h-full rounded-full transition-all duration-150"
          :class="phase === 'done' ? 'bg-settled' : 'bg-path'"
          :style="{ width: (totalFrames > 0 ? (frameIndex / totalFrames * 100) : 0) + '%' }"
        />
      </div>
      <div class="flex items-center justify-center gap-1">
        <button
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="frameIndex === 0"
          title="Step Back"
          @click="emit('stepBack')"
        >⏮</button>
        <button
          v-if="isPlaying"
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover"
          title="Pause"
          @click="emit('pause')"
        >⏸</button>
        <button
          v-else
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="phase !== 'explored'"
          title="Play"
          @click="emit('play')"
        >▶️</button>
        <button
          class="flex size-7 items-center justify-center rounded-md text-xs transition-colors hover:bg-surface-hover disabled:opacity-30"
          :disabled="phase !== 'explored' || frameIndex >= totalFrames"
          title="Step Forward"
          @click="emit('stepFwd')"
        >⏭</button>
      </div>
      <div class="mt-1 text-center font-mono text-[10px] text-text-secondary">
        <span v-if="phaseLabel">{{ phaseLabel }} </span>
        <span>{{ frameIndex }}/{{ totalFrames }}</span>
      </div>
    </div>
  </div>
</template>
