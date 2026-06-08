<script setup lang="ts">
import AlgoSelector from './AlgoSelector.vue'

interface LatLng {
  lat: number
  lng: number
}

defineProps<{
  start: LatLng | null
  end: LatLng | null
  selecting: 'start' | 'end'
  loading: boolean
  routeCost: number | null
  routeAttempted: boolean
  routeDetail: string
  locked: boolean
  error: string
  algorithm: string
}>()

const emit = defineEmits<{
  clear: []
  findRoute: []
  'update:selecting': [mode: 'start' | 'end']
  'update:algorithm': [value: string]
}>()

function fmt(ll: LatLng): string {
  return `${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}`
}

function formatEta(distKm: number): string {
  const minutes = Math.round(distKm / 40 * 60)
  if (minutes < 60) return `~${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `~${h}h ${m}min` : `~${h}h`
}
</script>

<template>
  <div
    class="pointer-events-auto absolute left-3 top-3 z-[500] w-44 sm:w-52 lg:w-64 rounded-xl
           border border-border bg-surface-panel/90 p-3 sm:p-4 shadow-lg backdrop-blur-md"
  >
    <h2 class="mb-3 text-sm font-semibold text-text-primary">Route</h2>

    <div class="mb-3 space-y-2">
      <div class="flex items-center gap-2">
        <span class="size-2.5 shrink-0 rounded-full bg-path" />
        <span v-if="start" class="font-mono text-[11px] sm:text-xs truncate text-text-primary">{{ fmt(start) }}</span>
        <span v-else class="text-xs text-text-secondary">No start</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="size-2.5 shrink-0 rounded-full bg-traffic" />
        <span v-if="end" class="font-mono text-[11px] sm:text-xs truncate text-text-primary">{{ fmt(end) }}</span>
        <span v-else class="text-xs text-text-secondary">No end</span>
      </div>
    </div>

    <div class="mb-3 flex gap-2">
      <button
        class="flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-150 active:scale-95"
        :disabled="locked"
        :class="selecting === 'start' && !locked
          ? 'bg-path text-white ring-2 ring-path-light'
          : locked
            ? 'border border-border text-text-secondary/40 cursor-not-allowed'
            : 'border border-border text-text-secondary hover:bg-surface-elevated'"
        @click="emit('update:selecting', 'start')"
      >
        ● Start
      </button>
      <button
        class="flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-150 active:scale-95"
        :disabled="locked"
        :class="selecting === 'end' && !locked
          ? 'bg-traffic text-white ring-2 ring-traffic-light'
          : locked
            ? 'border border-border text-text-secondary/40 cursor-not-allowed'
            : 'border border-border text-text-secondary hover:bg-surface-elevated'"
        @click="emit('update:selecting', 'end')"
      >
        ● End
      </button>
    </div>

    <div class="mb-3">
      <label class="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-text-secondary">Algorithm</label>
      <AlgoSelector
        :algorithm="algorithm"
        :disabled="loading"
        @update:algorithm="emit('update:algorithm', $event)"
      />
    </div>

    <div v-if="routeCost !== null && routeCost >= 0" class="mb-3 rounded-lg bg-surface-elevated px-3 py-2">
      <div class="flex items-center justify-between">
        <span class="text-xs text-text-secondary">Distance</span>
        <span class="font-mono text-sm text-settled">{{ routeCost.toFixed(4) }} km</span>
      </div>
      <div class="mt-1 flex items-center justify-between border-t border-border/40 pt-1">
        <span class="text-xs text-text-secondary">Est. drive time</span>
        <span class="font-mono text-xs text-frontier">{{ formatEta(routeCost) }}</span>
      </div>
    </div>

    <div v-if="routeAttempted && routeCost !== null && routeCost < 0" class="mb-3 rounded-lg bg-surface-elevated px-3 py-2">
      <span class="text-xs text-destructive">No path found</span>
      <p v-if="routeDetail" class="mt-1 text-[10px] text-text-secondary leading-tight">{{ routeDetail }}</p>
    </div>

    <div v-if="error" class="mb-3 rounded-lg bg-destructive/10 px-3 py-2">
      <span class="text-xs text-destructive">{{ error }}</span>
    </div>

    <div class="flex gap-2">
      <button
        :disabled="!start || !end || loading"
        class="flex-1 rounded-lg bg-path px-3 py-1.5 text-xs font-semibold text-white
               transition-all duration-150 hover:bg-path-light disabled:opacity-30
               disabled:cursor-not-allowed active:scale-95"
        @click="emit('findRoute')"
      >
        <span v-if="loading" class="inline-block animate-pulse">Routing…</span>
        <span v-else>Find Route</span>
      </button>

      <button
        :disabled="!start && !end"
        class="rounded-lg border border-border px-3 py-1.5 text-xs font-medium
               text-text-secondary transition-all duration-150 hover:bg-surface-elevated
               disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
        @click="emit('clear')"
      >
        Clear
      </button>
    </div>

    <p class="mt-2 text-[10px] text-text-secondary leading-tight">
      {{ locked ? 'Visualization in progress. Click Clear to start over.' : 'Select Start or End mode above, then click the map. Click same pin to deselect.' }}
    </p>
  </div>
</template>
