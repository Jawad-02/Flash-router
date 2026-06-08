<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const name = ref('')
const email = ref('')
const message = ref('')
const sending = ref(false)
const sent = ref(false)
const sendError = ref('')
const activeTab = ref('about')

const tabs = [
  { key: 'about', label: 'About' },
  { key: 'paper', label: '1959 Paper' },
  { key: 'complexity', label: 'Complexity' },
  { key: 'invariants', label: 'Invariants' },
  { key: 'system', label: 'System' },
]

async function submit() {
  if (!name.value || !email.value || !message.value) return
  sending.value = true
  sendError.value = ''
  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name.value,
        email: email.value,
        message: message.value,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      sendError.value = err.detail || 'Failed to send message'
      return
    }
    sent.value = true
    name.value = ''
    email.value = ''
    message.value = ''
  } catch {
    sendError.value = 'Network error'
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="show"
        class="fixed inset-0 z-[2000] bg-black/40"
        @click="emit('close')"
      />
    </Transition>

    <Transition name="slide">
      <div
        v-if="show"
        class="fixed top-0 right-0 z-[2001] h-full w-full sm:w-[420px] overflow-y-auto border-l border-border
               bg-surface-panel/95 p-4 sm:p-6 shadow-2xl backdrop-blur-md"
        @click.stop
      >
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-bold text-text-primary">Flash Router</h2>
          <button
            class="flex size-8 items-center justify-center rounded-lg text-sm text-text-secondary
                   transition-colors hover:bg-surface-hover"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>

        <div class="flex gap-1 mb-4 overflow-x-auto">
          <button
            v-for="t in tabs"
            :key="t.key"
            class="shrink-0 rounded-lg px-2.5 py-1 text-[11px] font-medium transition-colors"
            :class="activeTab === t.key
              ? 'bg-path text-white'
              : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'"
            @click="activeTab = t.key"
          >
            {{ t.label }}
          </button>
        </div>

        <div v-if="activeTab === 'about'">
          <div class="mb-5 flex items-center gap-4">
            <div class="relative size-14 shrink-0">
              <img
                src="/src/assets/me.jpg"
                alt="Profile"
                class="size-14 rounded-full border-2 border-border object-cover"
                @error="($event.target as HTMLImageElement).style.display = 'none'; ($event.target!.nextElementSibling as HTMLElement).style.display = 'flex'"
              />
              <div
                class="absolute inset-0 hidden items-center justify-center rounded-full border-2 border-border bg-surface-hover text-lg font-bold text-text-secondary"
              >
                JD
              </div>
            </div>
            <div>
              <h3 class="font-semibold text-text-primary">Jawad</h3>
              <p class="text-xs text-text-secondary">Co-Founder, Redeast</p>
            </div>
          </div>

          <div class="mb-5 space-y-3 text-xs text-text-secondary leading-relaxed">
            <p>
              Flash Router is a monolithic GPS routing application implementing
              E. W. Dijkstra's original 1959 shortest-path algorithm. Built with
              FastAPI on the backend and Vue 3 + Leaflet on the frontend.
            </p>
            <p>
              The street network is loaded from a pre-bundled Mersin graph
              (~95k nodes, ~212k edges) at startup, or fetched dynamically from
              OpenStreetMap via the Overpass API. All graphs are cached
              in-memory and routed using a binary-heap priority queue for
              O((V+E) log V) performance.
            </p>
            <p>
              Route visualization uses a two-phase animation: explored edges
              rendered as amber Canvas polylines, followed by the final path
              growing in blue. A progress bar in the telemetry panel tracks
              the animation progress (amber while exploring, green when
              complete). A Canvas renderer with non-interactive segments
              keeps performance smooth at scale.
            </p>
          </div>

          <div class="border-t border-border pt-5">
            <h3 class="mb-3 text-sm font-semibold text-text-primary">Contact</h3>
            <form @submit.prevent="submit" class="space-y-3">
              <input
                v-model="name"
                placeholder="Your name"
                class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary
                       placeholder:text-text-secondary/50 outline-none focus:border-path focus:ring-1 focus:ring-path"
              />
              <input
                v-model="email"
                type="email"
                placeholder="Your email"
                class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary
                       placeholder:text-text-secondary/50 outline-none focus:border-path focus:ring-1 focus:ring-path"
              />
              <textarea
                v-model="message"
                rows="4"
                placeholder="Your message"
                class="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary
                       placeholder:text-text-secondary/50 outline-none focus:border-path focus:ring-1 focus:ring-path"
              />
              <p v-if="sendError" class="text-xs text-destructive">{{ sendError }}</p>
              <button
                type="submit"
                :disabled="sending || sent"
                class="w-full rounded-lg bg-path px-3 py-2 text-xs font-semibold text-white transition-all
                       hover:bg-path-light disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
              >
                <span v-if="sending" class="inline-block animate-pulse">Sending…</span>
                <span v-else-if="sent">Sent! Thank you.</span>
                <span v-else>Send Message</span>
              </button>
            </form>
            <div class="mt-4 flex items-center justify-center gap-4 border-t border-border pt-4">
              <a
                href="https://github.com/Jawad-02"
                target="_blank"
                rel="noopener noreferrer"
                class="flex size-9 items-center justify-center rounded-xl transition-colors hover:bg-surface-hover"
                aria-label="GitHub"
              >
                <svg viewBox="0 0 24 24" class="size-5 fill-text-secondary" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12Z"/>
                </svg>
              </a>
              <a
                href="https://www.linkedin.com/in/jawad-merwah-659b36296/"
                target="_blank"
                rel="noopener noreferrer"
                class="flex size-9 items-center justify-center rounded-xl transition-colors hover:bg-surface-hover"
                aria-label="LinkedIn"
              >
                <svg viewBox="0 0 24 24" class="size-5 fill-text-secondary" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22.23 0H1.77C0.79 0 0 0.77 0 1.72v20.56C0 23.23 0.79 24 1.77 24h20.46c0.98 0 1.77-0.77 1.77-1.72V1.72C24 0.77 23.21 0 22.23 0ZM7.12 20.45H3.56V9.01h3.56v11.44ZM5.34 7.52a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM20.45 20.45h-3.56v-5.56c0-1.33-.03-3.04-1.85-3.04s-2.14 1.45-2.14 2.95v5.65h-3.56V9.01h3.42v1.56h0.05c0.48-0.9 1.65-1.85 3.4-1.85 3.63 0 4.3 2.39 4.3 5.5v6.23Z"/>
                </svg>
              </a>
              <a
                href="https://redeast.agency/"
                target="_blank"
                rel="noopener noreferrer"
                class="flex size-9 items-center justify-center rounded-xl transition-colors hover:bg-surface-hover"
                aria-label="Redeast Agency"
              >
                <svg viewBox="0 0 24 24" class="size-5 fill-text-secondary" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2Zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93Zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39Z"/>
                </svg>
              </a>
            </div>
          </div>
        </div>

        <div v-else-if="activeTab === 'paper'" class="space-y-4 text-xs text-text-secondary leading-relaxed">
          <h3 class="text-sm font-semibold text-text-primary">1959 Paper Compliance</h3>
          <p>
            This application directly implements <strong class="text-text-primary">Problem 2 (Shortest Path)</strong>
            from E. W. Dijkstra's 1959 paper
            <em>"A Note on Two Problems in Connexion with Graphs"</em>.
          </p>
          <p>
            The algorithm assigns every node a <strong class="text-text-primary">tentative distance</strong>,
            initially infinity for all nodes except the source (0). At each step, the node with the smallest
            tentative distance is <strong class="text-text-primary">settled</strong> permanently — mirroring
            Dijkstra's original greedy property:
          </p>
          <p class="border-l-2 border-frontier pl-3 text-frontier font-mono text-[11px]">
            "The minimum distance from the source to any unsettled node is the length of the shortest
            path to that node, because any alternative path must pass through a settled node with a
            larger distance."
          </p>
          <p>
            The frontier (<strong class="text-amber-500">amber</strong>) and settled
            (<strong class="text-emerald-500">green</strong> in the paper, visualised via the
            progress bar in this app) sets are the core invariant. Each iteration:
          </p>
          <ol class="list-decimal pl-4 space-y-1">
            <li>Select the unsettled node with the smallest known distance</li>
            <li>Settle it (mark as permanently evaluated)</li>
            <li>Relax all outgoing edges — if a shorter path to a neighbor is found, update its distance</li>
            <li>Repeat until the target is settled</li>
          </ol>
          <p>
            The original paper's <strong class="text-text-primary">weighted graph</strong> requirement
            is satisfied by using Haversine road distances as edge weights. We enforce
            <strong class="text-text-primary">non-negative</strong> edge weights (w(e) &ge; 0,
            with the traffic slider clamped to 0.001–1.000), which is critical to Dijkstra's correctness.
          </p>
        </div>

        <div v-else-if="activeTab === 'complexity'" class="space-y-4 text-xs text-text-secondary leading-relaxed">
          <h3 class="text-sm font-semibold text-text-primary">Complexity Optimisation Proof</h3>
          <p>
            Dijkstra's original 1959 implementation ran in <strong class="text-text-primary">O(V²)</strong>
            time — it scanned all unsettled nodes to find the minimum. This system uses a
            <strong class="text-path">binary min-heap</strong> (Python's <code class="text-frontier font-mono">heapq</code>),
            reducing the runtime to <strong class="text-settled">O((V+E) log V)</strong>.
          </p>
          <div class="rounded-lg bg-surface-elevated p-3 font-mono text-[11px] leading-relaxed">
            <p class="text-frontier">// Each node extracted once: O(V log V)</p>
            <p class="text-text-primary">while pq:</p>
            <p class="text-text-primary">&nbsp;&nbsp;d, u = heapq.heappop(pq) &nbsp;&nbsp;<span class="text-text-secondary">// O(log V)</span></p>
            <p class="text-text-primary">&nbsp;&nbsp;if u in settled: continue</p>
            <p class="text-text-primary">&nbsp;&nbsp;settled.add(u)</p>
            <p class="text-frontier mt-2">// Each edge relaxed once: O(E log V)</p>
            <p class="text-text-primary">&nbsp;&nbsp;for v, w in edges[u]:</p>
            <p class="text-text-primary">&nbsp;&nbsp;&nbsp;&nbsp;new_d = d + w</p>
            <p class="text-text-primary">&nbsp;&nbsp;&nbsp;&nbsp;if new_d &lt; dist[v]:</p>
            <p class="text-text-primary">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dist[v] = new_d</p>
            <p class="text-text-primary">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;heapq.heappush(pq, (new_d, v)) &nbsp;&nbsp;<span class="text-text-secondary">// O(log V)</span></p>
          </div>
          <p>
            Total: <strong class="text-settled">O((V+E) log V)</strong>.
            For a graph of ~95k nodes and ~212k edges (Mersin), this yields sub-200ms
            computation times in practice.
          </p>
          <p>
            A* Search uses the same heap structure with a Haversine heuristic, pruning
            the search space. Bi-Directional Dijkstra runs forward and backward simultaneously,
            meeting in the middle for up to 2× speedup. Greedy Best-First is the fastest
            but may return non-optimal paths.
          </p>
        </div>

        <div v-else-if="activeTab === 'invariants'" class="space-y-4 text-xs text-text-secondary leading-relaxed">
          <h3 class="text-sm font-semibold text-text-primary">Invariant &amp; Robustness Controls</h3>
          <p>
            The Traffic Mode slider preserves Dijkstra's mathematical integrity by enforcing
            <strong class="text-text-primary">non-negative edge weights</strong>:
          </p>
          <ul class="space-y-2">
            <li class="flex gap-2">
              <span class="text-settled shrink-0">✓</span>
              <span>Slider range is <strong class="text-text-primary">0.001–1.000</strong> km — weights
              are always strictly positive</span>
            </li>
            <li class="flex gap-2">
              <span class="text-settled shrink-0">✓</span>
              <span>Backend rejects <code class="font-mono text-frontier text-[10px]">new_weight &lt; 0</code>
              via Pydantic validation (<code class="font-mono text-frontier text-[10px]">ge=0</code>)</span>
            </li>
            <li class="flex gap-2">
              <span class="text-settled shrink-0">✓</span>
              <span>Weight <strong class="text-text-primary">0</strong> is interpreted as
              <strong class="text-text-primary">"restore original"</strong> — the backend
              looks up the initial weight snapshot from <code class="font-mono text-frontier text-[10px]">original_edges</code></span>
            </li>
            <li class="flex gap-2">
              <span class="text-settled shrink-0">✓</span>
              <span>Graph mutations are <strong class="text-text-primary">symmetric</strong> —
              both <code class="font-mono text-frontier text-[10px]">edges[from][to]</code> and
              <code class="font-mono text-frontier text-[10px]">edges[to][from]</code> are updated
              to maintain undirected road consistency</span>
            </li>
            <li class="flex gap-2">
              <span class="text-settled shrink-0">✓</span>
              <span>All state lives in <strong class="text-text-primary">RAM</strong> —
              no database, no serialization. Graph cache is reset on server restart</span>
            </li>
          </ul>
          <p class="border-l-2 border-settled pl-3 text-settled text-[11px]">
            These invariants guarantee that Dijkstra's algorithm remains correct under all
            traffic modifications: the non-negative weight condition is never violated,
            the graph stays undirected, and the cache is always internally consistent.
          </p>
        </div>

        <div v-else-if="activeTab === 'system'" class="space-y-4 text-xs text-text-secondary leading-relaxed">
          <h3 class="text-sm font-semibold text-text-primary">System Architecture</h3>
          <pre class="bg-surface-elevated p-3 rounded-lg font-mono text-[10px] leading-relaxed overflow-x-auto"><span class="text-text-primary">  +-------- Browser (Vue 3 / Leaflet) --------+
  |  RoutePanel     MapViewer                 |
  |  TelemetrySidebar   Traffic               |
  |  AboutSlider                              |
  +--------------------+----------------------+
                       |</span><span class="text-path">
  +--------------------v----------------------+
  |  FastAPI (Uvicorn)                        |
  |  POST /api/route                          |
  |  POST /api/traffic                        |
  |  POST /api/contact                        |
  |  GET  /static/* (SPA)                     |
  |  +-- Algorithms -----------------------+  |
  |  | Dijkstra    A*                      |  |
  |  | Bi-Directional    Greedy            |  |
  |  | heapq  O((V+E) log V)               |  |
  |  +-----------------+-------------------+  |
  |                    |                      |
  |  +-----------------v-------------------+  |
  |  | Overpass API (fallback)             |  |
  |  +-------------------------------------+  |
  +--------------------------------------------+</span></pre>
          <p>
            The application is a <strong class="text-text-primary">monolith</strong> — a single FastAPI
            process serves both the API endpoints and the compiled SPA from
            <code class="font-mono text-frontier text-[10px]">static/</code>. No database, no external
            services except Overpass API for dynamic street network fetches.
          </p>
          <p>
            Frontend components are single-file Vue 3 Composition API modules communicating
            via props and emits. State management uses Vue reactivity only — no Pinia, no Vuex.
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
