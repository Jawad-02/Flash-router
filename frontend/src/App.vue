<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import MapViewer from './components/MapViewer.vue'
import RoutePanel from './components/RoutePanel.vue'
import TrafficPanel from './components/TrafficPanel.vue'
import AboutSlider from './components/AboutSlider.vue'
import TelemetrySidebar from './components/TelemetrySidebar.vue'
import MobilePlaybackBar from './components/MobilePlaybackBar.vue'

interface LatLng {
  lat: number
  lng: number
}

const isDarkMode = ref(true)
const showAbout = ref(false)

const start = ref<LatLng | null>(null)
const end = ref<LatLng | null>(null)
const selecting = ref<'start' | 'end'>('start')
const routePath = ref<[number, number][]>([])
const exploredEdges = ref<(number | string)[][]>([])
const routeCost = ref<number | null>(null)
const routeDetail = ref('')
const loading = ref(false)
const loadingMessage = ref('')
const routeAttempted = ref(false)
const errorMsg = ref('')
const locked = ref(false)
const algorithm = ref('')
const computationMs = ref(0)
const exploredTotal = ref(0)
const exploredRendered = ref(0)
const pathEdgeCount = ref(0)
const trafficMode = ref(false)
const areaKey = ref('')
const noticeMsg = ref('')
const noticeVisible = ref(false)
const searchVersion = ref(0)
const reRoutePath = ref<[number, number][]>([])
const crowdedEdges = ref<Map<string, { from_id: string; to_id: string; weight: number }>>(new Map())
const crowdedEdgesArray = ref<{ from_id: string; to_id: string; weight: number }[]>([])
const clearCounter = ref(0)
const trafficHintVisible = ref(true)
const playbackCommand = ref<string | null>(null)
const frameIndex = ref(0)
const totalFrames = ref(0)
const animationPhase = ref('idle')
const isPlaying = ref(false)

function onPlay() { playbackCommand.value = 'play'; nextTick(() => { playbackCommand.value = null }) }
function onPause() { playbackCommand.value = 'pause'; nextTick(() => { playbackCommand.value = null }) }
function onStepFwd() { playbackCommand.value = 'stepFwd'; nextTick(() => { playbackCommand.value = null }) }
function onStepBack() { playbackCommand.value = 'stepBack'; nextTick(() => { playbackCommand.value = null }) }

function handleFrameUpdate(info: { frameIndex: number; totalFrames: number; phase: string; isPlaying: boolean }) {
  frameIndex.value = info.frameIndex
  totalFrames.value = info.totalFrames
  animationPhase.value = info.phase
  isPlaying.value = info.isPlaying
}

watch(trafficMode, (val) => {
  if (val && exploredEdges.value.length === 0) {
    trafficMode.value = false
    noticeMsg.value = 'Please find a route first before using Traffic mode.'
    noticeVisible.value = true
    return
  }
  if (val && algorithm.value !== '') {
    trafficMode.value = false
    noticeMsg.value = 'Traffic optimization is not available on this algorithm yet.'
    noticeVisible.value = true
    return
  }
  if (val) trafficHintVisible.value = true
})

watch(algorithm, () => {
  if (trafficMode.value && algorithm.value !== '') {
    trafficMode.value = false
    noticeMsg.value = 'Traffic optimization is not available on this algorithm yet.'
    noticeVisible.value = true
  }
})

function haversineKm(a: LatLng, b: LatLng): number {
  const R = 6371
  const dlat = (b.lat - a.lat) * Math.PI / 180
  const dlng = (b.lng - a.lng) * Math.PI / 180
  const sinLat = Math.sin(dlat / 2)
  const sinLng = Math.sin(dlng / 2)
  const a2 = sinLat * sinLat + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * sinLng * sinLng
  return R * 2 * Math.atan2(Math.sqrt(a2), Math.sqrt(1 - a2))
}

function approxEq(a: LatLng, b: LatLng): boolean {
  return Math.abs(a.lat - b.lat) < 0.0005 && Math.abs(a.lng - b.lng) < 0.0005
}

function onMapClick(latlng: LatLng) {
  if (locked.value) return

  errorMsg.value = ''

  if (start.value && approxEq(latlng, start.value)) {
    start.value = null
    selecting.value = 'start'
    routePath.value = []
    exploredEdges.value = []
    routeCost.value = null
    routeAttempted.value = false
    clearCounter.value++
    searchVersion.value = 0
    reRoutePath.value = []
    crowdedEdges.value = new Map()
    crowdedEdgesArray.value = []
    trafficMode.value = false
    trafficHintVisible.value = false
    noticeVisible.value = false
    return
  }
  if (end.value && approxEq(latlng, end.value)) {
    end.value = null
    selecting.value = 'end'
    routePath.value = []
    exploredEdges.value = []
    routeCost.value = null
    routeAttempted.value = false
    clearCounter.value++
    searchVersion.value = 0
    reRoutePath.value = []
    crowdedEdges.value = new Map()
    crowdedEdgesArray.value = []
    trafficMode.value = false
    trafficHintVisible.value = false
    noticeVisible.value = false
    return
  }

  if (selecting.value === 'start') {
    start.value = latlng
    selecting.value = 'end'
  } else {
    end.value = latlng
  }

  routePath.value = []
  exploredEdges.value = []
  routeCost.value = null
  routeAttempted.value = false
  clearCounter.value++
  searchVersion.value = 0
  reRoutePath.value = []
  crowdedEdges.value = new Map()
  crowdedEdgesArray.value = []
  trafficMode.value = false
  trafficHintVisible.value = false
  noticeVisible.value = false
}

const maxDistKm = 50

async function findRoute() {
  if (!start.value || !end.value) return

  const d = haversineKm(start.value, end.value)
  if (d > maxDistKm) {
    errorMsg.value = `Distance ${d.toFixed(1)} km exceeds the ${maxDistKm} km limit.`
    return
  }

  routePath.value = []
  exploredEdges.value = []
  routeCost.value = null
  loading.value = true
  loadingMessage.value = 'Computing shortest path…'
  errorMsg.value = ''
  routeDetail.value = ''
  try {
    const res = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: start.value.lat,
        start_lng: start.value.lng,
        end_lat: end.value.lat,
        end_lng: end.value.lng,
        algorithm: algorithm.value,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      errorMsg.value = err.detail || 'Route request failed'
      loading.value = false
      return
    }

    loadingMessage.value = 'Building visualization…'
    const data = await res.json()
    routePath.value = data.route_path || []
    exploredEdges.value = (data.explored_edges || []).map(
      (e: (number | string)[]) => e as (number | string)[],
    )
    searchVersion.value++
    routeCost.value = data.cost
    routeDetail.value = data.detail || ''
    routeAttempted.value = true
    locked.value = true
    computationMs.value = data.computation_ms || 0
    areaKey.value = data.area_key || ''
    exploredTotal.value = (data.explored_edges || []).length
    exploredRendered.value = Math.min(exploredTotal.value, 150000)
    pathEdgeCount.value = (data.route_path || []).length - 1
  } catch {
    errorMsg.value = 'Network error'
    routeAttempted.value = true
  } finally {
    loading.value = false
    loadingMessage.value = ''
  }
}

function clearSelection() {
  start.value = null
  end.value = null
  selecting.value = 'start'
  routePath.value = []
  exploredEdges.value = []
  routeCost.value = null
  routeDetail.value = ''
  errorMsg.value = ''
  routeAttempted.value = false
  locked.value = false
  computationMs.value = 0
  exploredTotal.value = 0
  exploredRendered.value = 0
  pathEdgeCount.value = 0
  areaKey.value = ''
  searchVersion.value = 0
  clearCounter.value++
  reRoutePath.value = []
  crowdedEdges.value = new Map()
  crowdedEdgesArray.value = []
  trafficMode.value = false
  trafficHintVisible.value = true
  noticeVisible.value = false
}

function handleReRouteDone() {
  routePath.value = reRoutePath.value
  reRoutePath.value = []
}

const trafficQueue: { from_id: string; to_id: string; new_weight: number }[] = []
let trafficBusy = false

async function processTrafficQueue() {
  const edge = trafficQueue.shift()
  if (!edge) return
  trafficBusy = true
  loading.value = true
  loadingMessage.value = edge.new_weight === 0 ? 'Removing congestion…' : 'Re-routing with traffic updates…'
  try {
    const res = await fetch('/api/traffic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        area_key: areaKey.value,
        edge_from: edge.from_id,
        edge_to: edge.to_id,
        new_weight: edge.new_weight,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      errorMsg.value = err.detail || 'Traffic update failed'
      loading.value = false
      trafficBusy = false
      processTrafficQueue()
      return
    }

    const key = `${edge.from_id}→${edge.to_id}`
    if (edge.new_weight === 0) {
      crowdedEdges.value.delete(key)
    } else {
      crowdedEdges.value.set(key, {
        from_id: edge.from_id,
        to_id: edge.to_id,
        weight: edge.new_weight,
      })
    }
    crowdedEdgesArray.value = Array.from(crowdedEdges.value.values())

    const routeRes = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: start.value!.lat,
        start_lng: start.value!.lng,
        end_lat: end.value!.lat,
        end_lng: end.value!.lng,
        algorithm: algorithm.value,
      }),
    })

    if (!routeRes.ok) {
      const err = await routeRes.json()
      errorMsg.value = err.detail || 'Re-route failed'
      loading.value = false
      trafficBusy = false
      processTrafficQueue()
      return
    }

    loadingMessage.value = 'Building visualization…'
    const data = await routeRes.json()
    computationMs.value = data.computation_ms || 0
    routeCost.value = data.cost
    exploredTotal.value = (data.explored_edges || []).length
    exploredRendered.value = Math.min(exploredTotal.value, 150000)
    pathEdgeCount.value = (data.route_path || []).length - 1
    reRoutePath.value = data.route_path || []
    areaKey.value = data.area_key || ''
  } catch {
    errorMsg.value = 'Traffic update failed'
  } finally {
    loading.value = false
    loadingMessage.value = ''
    trafficBusy = false
    processTrafficQueue()
  }
}

function handleEdgeModify(edge: { from_id: string; to_id: string; new_weight: number }) {
  if (!areaKey.value) return
  trafficQueue.push(edge)
  if (!trafficBusy) processTrafficQueue()
}
</script>

<template>
  <div class="h-dvh w-dvw flex flex-col overflow-hidden bg-surface" :class="{ 'is-dark': isDarkMode }">
    <header
      class="absolute top-0 left-0 right-0 z-[1000] flex items-center justify-between px-3 sm:px-4 py-2 sm:py-2.5
             bg-surface-panel/80 backdrop-blur-md border-b border-border"
    >
      <h1 class="flex items-center gap-2 text-base sm:text-lg font-bold tracking-tight">
        <span class="text-path text-xl sm:text-xl">⚡</span>
        <span class="hidden sm:inline">Flash Router</span>
      </h1>
      <div class="flex items-center gap-2">
        <button
          class="flex size-8 items-center justify-center rounded-lg text-lg transition-colors hover:bg-surface-hover"
          title="Toggle theme"
          @click="isDarkMode = !isDarkMode"
        >
          {{ isDarkMode ? '🌙' : '☀️' }}
        </button>
        <button
          class="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-hover"
          title="About"
          @click="showAbout = !showAbout"
        >
          About
        </button>
        <TrafficPanel v-model="trafficMode" />
      </div>
    </header>

    <main class="flex-1 relative mt-12">
      <RoutePanel
        :start="start"
        :end="end"
        :selecting="selecting"
        :loading="loading"
        :route-cost="routeCost"
        :route-attempted="routeAttempted"
        :route-detail="routeDetail"
        :locked="locked"
        :error="errorMsg"
        :algorithm="algorithm"
        @update:selecting="selecting = $event"
        @update:algorithm="algorithm = $event"
        @find-route="findRoute"
        @clear="clearSelection"
      />
      <MapViewer
        :start="start"
        :end="end"
        :route-path="routePath"
        :explored-edges="exploredEdges"
        :loading="loading"
        :loading-message="loadingMessage"
        :locked="locked"
        :is-dark-mode="isDarkMode"
        :traffic-mode="trafficMode"
        :re-route-path="reRoutePath"
        :crowded-edges="crowdedEdgesArray"
        :search-version="searchVersion"
        :clear-counter="clearCounter"
        :playback-command="playbackCommand"
        @map-click="onMapClick"
        @edge-modify="handleEdgeModify"
        @re-route-done="handleReRouteDone"
        @frame-update="handleFrameUpdate"
      />
      <div class="absolute z-[500] flex flex-col gap-2 left-3 sm:right-3 sm:top-3 sm:left-auto" :class="animationPhase !== 'idle' ? 'bottom-16' : 'bottom-3'">
        <TelemetrySidebar
          :algorithm="algorithm"
          :computation-ms="computationMs"
          :explored-total="exploredTotal"
          :explored-rendered="exploredRendered"
          :path-edge-count="pathEdgeCount"
          :route-cost="routeCost"
          :frame-index="frameIndex"
          :total-frames="totalFrames"
          :phase="animationPhase"
          :is-playing="isPlaying"
          @play="onPlay"
          @pause="onPause"
          @step-fwd="onStepFwd"
          @step-back="onStepBack"
        />
        <div
          v-if="trafficMode && trafficHintVisible"
          :class="[
            'w-44 sm:w-40 lg:w-56 rounded-xl border p-3 shadow-lg backdrop-blur-md',
            isDarkMode
              ? 'border-amber-500/30 bg-amber-500/10'
              : 'border-amber-300 bg-amber-50'
          ]"
        >
          <div class="flex items-start justify-between">
            <h3 :class="['text-xs font-semibold', isDarkMode ? 'text-amber-400' : 'text-amber-700']">Traffic Mode</h3>
            <button
              :class="['flex size-4 items-center justify-center text-[10px]', isDarkMode ? 'text-amber-400/60 hover:text-amber-400' : 'text-amber-600 hover:text-amber-800']"
              @click="trafficHintVisible = false"
            >✕</button>
          </div>
          <p :class="['mt-1 text-[10px] leading-relaxed', isDarkMode ? 'text-amber-300/80' : 'text-amber-800']">
            Click any road to adjust its weight.
            <span class="inline-block size-2 rounded-full bg-blue-500 align-middle" /> Blue = on your route,
            <span class="inline-block size-2 rounded-full bg-amber-500 align-middle" /> Amber = explored.
          </p>
        </div>
        <div
          v-if="noticeVisible"
          :class="[
            'w-44 sm:w-40 lg:w-56 rounded-xl border p-3 shadow-lg backdrop-blur-md',
            isDarkMode
              ? 'border-red-500/30 bg-red-500/10'
              : 'border-red-300 bg-red-50'
          ]"
        >
          <div class="flex items-start justify-between">
            <p :class="['text-[10px] leading-relaxed', isDarkMode ? 'text-red-300/90' : 'text-red-700']">
              {{ noticeMsg }}
            </p>
            <button
              :class="['flex size-4 shrink-0 items-center justify-center text-[10px]', isDarkMode ? 'text-red-400/60 hover:text-red-400' : 'text-red-600 hover:text-red-800']"
              @click="noticeVisible = false"
            >✕</button>
          </div>
        </div>
      </div>
      <AboutSlider :show="showAbout" @close="showAbout = false" />
      <MobilePlaybackBar
        :frame-index="frameIndex"
        :total-frames="totalFrames"
        :phase="animationPhase"
        :is-playing="isPlaying"
        @play="onPlay"
        @pause="onPause"
        @step-fwd="onStepFwd"
        @step-back="onStepBack"
      />
    </main>
  </div>
</template>
