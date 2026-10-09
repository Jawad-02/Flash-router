<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface LatLng {
  lat: number
  lng: number
}

interface EdgeData {
  from_id: string
  to_id: string
  weight: number
}

interface SegmentData {
  coords: [number, number][]
  from_id: string
  to_id: string
  weight: number
  originalWeight: number
}

const props = defineProps<{
  start: LatLng | null
  end: LatLng | null
  routePath: [number, number][]
  exploredEdges: (number | string)[][]
  loading: boolean
  loadingMessage: string
  locked: boolean
  isDarkMode: boolean
  trafficMode: boolean
  reRoutePath: [number, number][]
  crowdedEdges: { from_id: string; to_id: string; weight: number }[]
  searchVersion: number
  clearCounter: number
  playbackCommand: string | null
}>()

const emit = defineEmits<{
  mapClick: [latlng: LatLng]
  edgeModify: [edge: { from_id: string; to_id: string; new_weight: number }]
  reRouteDone: []
  frameUpdate: [{ frameIndex: number; totalFrames: number; phase: string; isPlaying: boolean }]
}>()

const mapContainer = ref(null)
let map: L.Map | null = null
let tileLayer: L.TileLayer | null = null
let startMarker: L.Marker | null = null
let endMarker: L.Marker | null = null
const canvasRenderer = L.canvas({ padding: 0.5, tolerance: 5 })
let routeLine: L.Polyline | null = null
let exploredGroup: L.LayerGroup | null = null
let exploredTimer: ReturnType<typeof setInterval> | null = null
let pathTimer: ReturnType<typeof setInterval> | null = null
let activePopup: L.Popup | null = null
let edgeMetaList: SegmentData[] = []
let oldRouteLine: L.Polyline | null = null
const oldCrowdedLines: L.Layer[] = []
let renderedEdgeCount = 0
const batchSize = ref(1)
const isPlaying = ref(false)
const animationPhase = ref<'idle' | 'explored' | 'path' | 'done'>('idle')
const frameIndex = ref(0)
const totalFrames = ref(0)

const blueIcon = L.divIcon({
  className: '',
  html: '<div style="width:24px;height:24px;background:#3b82f6;border:3px solid #93c5fd;border-radius:50%;transform:translate(-50%,-50%)"></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

const redIcon = L.divIcon({
  className: '',
  html: '<div style="width:24px;height:24px;background:#ef4444;border:3px solid #fca5a5;border-radius:50%;transform:translate(-50%,-50%)"></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

function onMapClickHandler(e: L.LeafletMouseEvent) {
  if (props.locked) return
  emit('mapClick', { lat: e.latlng.lat, lng: e.latlng.lng })
}

function updateStartMarker(latlng: LatLng | null) {
  if (startMarker) {
    startMarker.remove()
    startMarker = null
  }
  if (latlng) {
    startMarker = L.marker([latlng.lat, latlng.lng], { icon: blueIcon }).addTo(map!)
    startMarker.bindTooltip('Start', { permanent: true, direction: 'top', offset: [0, -16], className: 'marker-tooltip' })
  }
}

function updateEndMarker(latlng: LatLng | null) {
  if (endMarker) {
    endMarker.remove()
    endMarker = null
  }
  if (latlng) {
    endMarker = L.marker([latlng.lat, latlng.lng], { icon: redIcon }).addTo(map!)
    endMarker.bindTooltip('End', { permanent: true, direction: 'top', offset: [0, -16], className: 'marker-tooltip' })
  }
}

function clearTimers() {
  if (exploredTimer) { clearInterval(exploredTimer); exploredTimer = null }
  if (pathTimer) { clearInterval(pathTimer); pathTimer = null }
}

function clearOverlays() {
  clearTimers()
  if (activePopup) { map?.closePopup(); activePopup = null }
  if (exploredGroup) { exploredGroup.remove(); exploredGroup = null }
  if (routeLine) { routeLine.remove(); routeLine = null }
  if (oldRouteLine) { oldRouteLine.remove(); oldRouteLine = null }
  for (const p of oldCrowdedLines) p.remove()
  oldCrowdedLines.length = 0
  edgeMetaList = []
  isPlaying.value = false
  animationPhase.value = 'idle'
  frameIndex.value = 0
  totalFrames.value = 0
  renderedEdgeCount = 0
}

function rebuildExploredPolylines(interactive: boolean, routePathOverride?: [number, number][]) {
  if (!map || edgeMetaList.length < 1) return
  if (activePopup) { map.closePopup(); activePopup = null }

  const path = routePathOverride && routePathOverride.length >= 2 ? routePathOverride : props.routePath
  const routeSet = new Set<string>()
  if (interactive) {
    for (let i = 0; i < path.length - 1; i++) {
      const a = path[i]
      const b = path[i + 1]
      routeSet.add(`${a[0]},${a[1]}→${b[0]},${b[1]}`)
    }
  }

  const newGroup = L.layerGroup()
  for (const seg of edgeMetaList) {
    const onRoute = interactive && routeSet.has(
      `${seg.coords[0][0]},${seg.coords[0][1]}→${seg.coords[1][0]},${seg.coords[1][1]}`
    )
    const polyline = L.polyline(seg.coords, {
      color: onRoute ? '#3b82f6' : '#f59e0b',
      weight: onRoute ? 3 : 2,
      opacity: 0.5,
      interactive,
      renderer: canvasRenderer,
    })
    if (interactive) {
      polyline.on('click', (e: L.LeafletMouseEvent) => {
        showTrafficPopup(e.latlng, {
          from_id: seg.from_id,
          to_id: seg.to_id,
          weight: seg.weight,
        })
      })
    }
    newGroup.addLayer(polyline)
  }

  if (exploredGroup) exploredGroup.remove()
  exploredGroup = newGroup.addTo(map)
  renderedEdgeCount = edgeMetaList.length
}

function showCrowdedOverlays() {
  if (!map) return
  const crowdedKeys = new Set(props.crowdedEdges.map(
    e => `${e.from_id}→${e.to_id}`
  ))

  for (const seg of edgeMetaList) {
    const key = `${seg.from_id}→${seg.to_id}`
    if (!crowdedKeys.has(key)) continue

    const crowdInfo = props.crowdedEdges.find(e => `${e.from_id}→${e.to_id}` === key)
    const poly = L.polyline(seg.coords, {
      color: '#ef4444',
      weight: 6,
      opacity: 0.9,
      interactive: false,
    }).addTo(map)
    oldCrowdedLines.push(poly)
    if (crowdInfo) {
      poly.bindTooltip(`${crowdInfo.weight.toFixed(3)}`, {
        permanent: true,
        direction: 'top',
        offset: L.point(0, -5),
        className: 'crowded-tooltip',
      })
    }
  }
}

function showTrafficPopup(latlng: L.LatLng, edge: EdgeData) {
  if (!map) return
  if (activePopup) map.closePopup()

  const container = document.createElement('div')
  container.style.cssText = 'padding:4px 0;min-width:170px;'

  const label = document.createElement('label')
  label.style.cssText = 'display:block;font-size:11px;font-weight:600;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em;'
  label.textContent = 'Traffic Weight'
  container.appendChild(label)

  const row = document.createElement('div')
  row.style.cssText = 'display:flex;align-items:center;gap:8px;'

  const slider = document.createElement('input')
  slider.type = 'range'
  slider.min = '0.001'
  slider.max = '1.000'
  slider.step = '0.001'
  slider.value = edge.weight.toFixed(3)
  slider.style.cssText = 'flex:1;accent-color:#f59e0b;height:4px;'
  row.appendChild(slider)

  const valSpan = document.createElement('span')
  valSpan.style.cssText = 'font-family:monospace;font-size:11px;min-width:48px;text-align:right;'
  valSpan.textContent = edge.weight.toFixed(3)
  row.appendChild(valSpan)

  container.appendChild(row)

  slider.addEventListener('input', () => {
    valSpan.textContent = parseFloat(slider.value).toFixed(3)
  })

  slider.addEventListener('change', () => {
    const newWeight = parseFloat(slider.value)
    emit('edgeModify', {
      from_id: edge.from_id,
      to_id: edge.to_id,
      new_weight: newWeight,
    })
  })

  const removeBtn = document.createElement('button')
  removeBtn.textContent = '✕ Remove'
  removeBtn.title = 'Reset to original weight'
  removeBtn.style.cssText = [
    'margin-top:8px;',
    'padding:3px 10px;',
    'border:1px solid #ef4444;',
    'border-radius:6px;',
    'background:transparent;',
    'color:#ef4444;',
    'font-size:10px;',
    'font-family:inherit;',
    'cursor:pointer;',
    'display:block;',
    'width:100%;',
    'text-align:center;',
  ].join('')
  removeBtn.addEventListener('click', () => {
    emit('edgeModify', {
      from_id: edge.from_id,
      to_id: edge.to_id,
      new_weight: 0,
    })
  })
  container.appendChild(removeBtn)

  activePopup = L.popup({
    className: 'traffic-popup',
    closeButton: false,
    offset: [0, 8],
  })
    .setLatLng(latlng)
    .setContent(container)
    .openOn(map)
}

function emitFrameUpdate() {
  emit('frameUpdate', {
    frameIndex: frameIndex.value,
    totalFrames: totalFrames.value,
    phase: animationPhase.value,
    isPlaying: isPlaying.value,
  })
}

function renderEdgeBatch(from: number, to: number) {
  if (!exploredGroup || !map) return
  for (let i = from; i < to && i < edgeMetaList.length; i++) {
    const seg = edgeMetaList[i]
    const polyline = L.polyline(seg.coords, {
      color: '#f59e0b', weight: 2, opacity: 0.5,
      interactive: props.trafficMode,
      renderer: canvasRenderer,
    })
    if (props.trafficMode) {
      polyline.on('click', (e: L.LeafletMouseEvent) => {
        showTrafficPopup(e.latlng, { from_id: seg.from_id, to_id: seg.to_id, weight: seg.weight })
      })
    }
    polyline.addTo(exploredGroup!)
  }
}

function rebuildFromScratch(count: number) {
  if (!map) return
  if (exploredGroup) exploredGroup.remove()
  exploredGroup = L.layerGroup().addTo(map!)
  renderEdgeBatch(0, count)
}

function play() {
  if (animationPhase.value !== 'explored') return
  if (exploredTimer) return
  isPlaying.value = true
  exploredTimer = setInterval(() => {
    if (renderedEdgeCount >= edgeMetaList.length) { pause(); return }
    const end = Math.min(renderedEdgeCount + batchSize.value, edgeMetaList.length)
    renderEdgeBatch(renderedEdgeCount, end)
    renderedEdgeCount = end
    frameIndex.value++
    emitFrameUpdate()
    if (renderedEdgeCount >= edgeMetaList.length) {
      pause()
      animationPhase.value = 'path'
      animatePath(props.routePath)
    }
  }, 16)
}

function pause() {
  isPlaying.value = false
  if (exploredTimer) { clearInterval(exploredTimer); exploredTimer = null }
}

function stepForward() {
  if (animationPhase.value !== 'explored' || renderedEdgeCount >= edgeMetaList.length) return
  const end = Math.min(renderedEdgeCount + batchSize.value, edgeMetaList.length)
  renderEdgeBatch(renderedEdgeCount, end)
  renderedEdgeCount = end
  frameIndex.value++
  emitFrameUpdate()
  if (renderedEdgeCount >= edgeMetaList.length) {
    animationPhase.value = 'path'
    animatePath(props.routePath)
  }
}

function stepBackward() {
  if (animationPhase.value === 'idle' || renderedEdgeCount === 0) return
  if (animationPhase.value !== 'explored') {
    if (pathTimer) { clearInterval(pathTimer); pathTimer = null }
    if (routeLine) { routeLine.remove(); routeLine = null }
    if (oldRouteLine) { oldRouteLine.remove(); oldRouteLine = null }
    for (const p of oldCrowdedLines) p.remove()
    oldCrowdedLines.length = 0
    animationPhase.value = 'explored'
  }
  const prevCount = Math.max(0, renderedEdgeCount - batchSize.value)
  renderedEdgeCount = prevCount
  frameIndex.value--
  rebuildFromScratch(renderedEdgeCount)
  emitFrameUpdate()
}

function animatePath(newPath: [number, number][]) {
  if (newPath.length < 2) return
  if (pathTimer) {
    clearInterval(pathTimer)
    pathTimer = null
  }
  if (routeLine) {
    routeLine.remove()
    routeLine = null
  }

  const targetMs = 1000
  const intervalMs = 16
  const totalFrames = Math.ceil(targetMs / intervalMs)
  const batchSize = Math.max(1, Math.floor(newPath.length / totalFrames))
  let idx = 0

  routeLine = L.polyline([], {
    color: '#3b82f6',
    weight: 4,
    opacity: 0.9,
    interactive: false,
  }).addTo(map!)

  pathTimer = setInterval(() => {
    const end = Math.min(idx + batchSize, newPath.length)
    routeLine!.setLatLngs(newPath.slice(0, end))
    idx = end
    if (idx >= newPath.length) {
      clearInterval(pathTimer!)
      pathTimer = null
      routeLine!.setStyle({ dashArray: '10, 6' })
      animationPhase.value = 'done'
      emitFrameUpdate()
      showCrowdedOverlays()
    }
  }, intervalMs)
}

function animateReRoute(newPath: [number, number][]) {
  if (newPath.length < 2) return
  if (pathTimer) {
    clearInterval(pathTimer)
    pathTimer = null
  }

  for (const p of oldCrowdedLines) p.remove()
  oldCrowdedLines.length = 0

  for (const seg of edgeMetaList) {
    const key = `${seg.from_id}→${seg.to_id}`
    const crowdInfo = props.crowdedEdges.find(e => `${e.from_id}→${e.to_id}` === key)
    seg.weight = crowdInfo ? crowdInfo.weight : seg.originalWeight
  }
  rebuildExploredPolylines(props.trafficMode, newPath)

  if (oldRouteLine) {
    oldRouteLine.setStyle({ color: '#ef4444', weight: 3, opacity: 0.4, dashArray: '6, 6' })
  }

  showCrowdedOverlays()

  const targetMs = 1000
  const intervalMs = 16
  const totalFrames = Math.ceil(targetMs / intervalMs)
  const batchSize = Math.max(1, Math.floor(newPath.length / totalFrames))
  let idx = 0

  routeLine = L.polyline([], {
    color: '#3b82f6',
    weight: 4,
    opacity: 0.9,
    interactive: false,
  }).addTo(map!)

  pathTimer = setInterval(() => {
    const end = Math.min(idx + batchSize, newPath.length)
    routeLine!.setLatLngs(newPath.slice(0, end))
    idx = end
    if (idx >= newPath.length) {
      clearInterval(pathTimer!)
      pathTimer = null
      routeLine!.setStyle({ dashArray: '10, 6' })
      emit('reRouteDone')
    }
  }, intervalMs)
}

function animateSearch() {
  clearOverlays()

  const edges = props.exploredEdges
  const path = props.routePath

  if (edges.length < 1) { animatePath(path); return }

  edgeMetaList = []
  for (const edge of edges) {
    const [fl, fn, tl, tn, fi, ti, w] = edge as [number, number, number, number, string, string, number]
    edgeMetaList.push({
      coords: [[fl, fn], [tl, tn]],
      from_id: fi,
      to_id: ti,
      weight: w,
      originalWeight: w,
    })
  }

  const numFrames = Math.ceil(1500 / 16)
  batchSize.value = Math.max(1, Math.floor(edgeMetaList.length / numFrames))
  totalFrames.value = Math.ceil(edgeMetaList.length / batchSize.value)
  renderedEdgeCount = 0
  frameIndex.value = 0
  animationPhase.value = 'explored'
  exploredGroup = L.layerGroup().addTo(map!)
  emitFrameUpdate()
  play()
}

watch(() => props.start, updateStartMarker, { deep: true })
watch(() => props.end, updateEndMarker, { deep: true })

watch(() => props.searchVersion, () => {
  if (!props.routePath || props.routePath.length < 2) return
  animateSearch()
})

watch(() => props.clearCounter, () => {
  clearOverlays()
})

watch(() => props.reRoutePath, (newPath) => {
  if (!newPath || newPath.length < 2) return
  if (oldRouteLine) {
    oldRouteLine.remove()
    oldRouteLine = null
    for (const p of oldCrowdedLines) p.remove()
    oldCrowdedLines.length = 0
  }
  if (props.crowdedEdges.length > 0 && routeLine) {
    oldRouteLine = routeLine
    routeLine = null
  } else if (routeLine) {
    routeLine.remove()
    routeLine = null
  }
  animateReRoute(newPath)
}, { deep: true })

watch(() => props.trafficMode, (interactive) => {
  if (exploredTimer || pathTimer) return
  if (routeLine) {
    routeLine.remove()
    routeLine = null
  }
  if (oldRouteLine && !interactive) {
    oldRouteLine.remove()
    oldRouteLine = null
    for (const p of oldCrowdedLines) p.remove()
    oldCrowdedLines.length = 0
  }
  rebuildExploredPolylines(interactive)
  if (!interactive && props.routePath.length >= 2) {
    routeLine = L.polyline(props.routePath as [number, number][], {
      color: '#3b82f6',
      weight: 4,
      opacity: 0.9,
      interactive: false,
    }).addTo(map!)
  }
})

watch(() => props.isDarkMode, (isDark) => {
  if (!map || !tileLayer) return
  tileLayer.remove()
  const url = isDark
    ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
  tileLayer = L.tileLayer(url, {
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxNativeZoom: 16,
    maxZoom: 20,
  }).addTo(map)
  if (mapContainer.value) {
    mapContainer.value.classList.toggle('light-mode', !isDark)
  }
})

watch(() => props.playbackCommand, (cmd) => {
  if (!cmd) return
  switch (cmd) {
    case 'play': play(); break
    case 'pause': pause(); break
    case 'stepFwd': stepForward(); break
    case 'stepBack': stepBackward(); break
  }
})

onMounted(() => {
  map = L.map(mapContainer.value!, {
    zoomControl: false,
    attributionControl: false,
  })

  tileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxNativeZoom: 16,
    maxZoom: 20,
  }).addTo(map)

  L.control.zoom({ position: 'bottomright' }).addTo(map)

  map.setView([36.80, 34.63], 14)

  map.on('click', onMapClickHandler)
})

onUnmounted(() => {
  clearOverlays()
  for (const p of oldCrowdedLines) p.remove()
  oldCrowdedLines.length = 0
  if (oldRouteLine) { oldRouteLine.remove(); oldRouteLine = null }
  isPlaying.value = false
  animationPhase.value = 'idle'
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="relative h-full w-full">
    <div ref="mapContainer" class="h-full w-full" />
    <div
      v-if="loading"
      class="absolute inset-0 z-[600] flex flex-col items-center justify-center gap-3 bg-black/40"
    >
      <div
        class="size-10 animate-spin rounded-full border-4 border-border border-t-path"
      />
      <p v-if="loadingMessage" class="font-mono text-xs text-white">{{ loadingMessage }}</p>
    </div>
  </div>
</template>

<style>
.marker-tooltip {
  background-color: #1e293b !important;
  color: #f8fafc !important;
  border: 1px solid #475569 !important;
  font-family: JetBrains Mono, monospace !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  padding: 2px 8px !important;
  border-radius: 6px !important;
}

.marker-tooltip::before {
  border-top-color: #475569 !important;
}

.traffic-popup .leaflet-popup-content-wrapper {
  background-color: #1e293b !important;
  color: #f8fafc !important;
  border: 1px solid #475569 !important;
  border-radius: 8px !important;
  font-family: JetBrains Mono, monospace !important;
  font-size: 11px !important;
}

.traffic-popup .leaflet-popup-tip {
  background-color: #1e293b !important;
  border: 1px solid #475569 !important;
}

.leaflet-control-zoom a {
  background-color: #1e293b !important;
  color: #f8fafc !important;
  border-color: #475569 !important;
}

.leaflet-control-zoom a:hover {
  background-color: #334155 !important;
}

.light-mode .marker-tooltip {
  background-color: #ffffff !important;
  color: #1e293b !important;
  border: 1px solid #d1d5db !important;
}

.light-mode .marker-tooltip::before {
  border-top-color: #d1d5db !important;
}

.light-mode .traffic-popup .leaflet-popup-content-wrapper {
  background-color: #ffffff !important;
  color: #1e293b !important;
  border: 1px solid #d1d5db !important;
}

.light-mode .traffic-popup .leaflet-popup-tip {
  background-color: #ffffff !important;
  border: 1px solid #d1d5db !important;
}

.light-mode .leaflet-control-zoom a {
  background-color: #ffffff !important;
  color: #374151 !important;
  border-color: #d1d5db !important;
}

.light-mode .leaflet-control-zoom a:hover {
  background-color: #f3f4f6 !important;
}

.crowded-tooltip {
  background: #ef4444 !important;
  color: #fff !important;
  border: none !important;
  font-family: JetBrains Mono, monospace !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
  white-space: nowrap !important;
}

.crowded-tooltip::before {
  border-top-color: #ef4444 !important;
}
</style>
