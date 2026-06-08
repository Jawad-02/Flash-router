# Flash Router

High-performance GPS routing application with interactive algorithmic visualization, real-time traffic simulation, and frame-by-frame playback controls. Built as a Vue 3 + FastAPI monolith.

## Features

- **Multi-Algorithm Engine** — Dijkstra, A\*, Bi-Directional Dijkstra, Greedy Best-First
- **Two-Phase Search Animation** — Watch the frontier expand (amber) then the shortest path grow (blue)
- **Playback Controls** — Play, Pause, Step Forward, Step Back with progress bar
- **Dynamic Traffic Mode** — Click any explored road to adjust its weight; see live re-routing
- **Academic Documentation** — 5-tab built-in reference: 1959 paper, complexity proof, invariants, system diagram
- **Responsive Design** — Desktop sidebar + mobile floating controls
- **Dark/Light Theme** — Toggle via floating action button
- **Static Mersin Graph** — 95K-node, 212K-edge pre-loaded network; dynamic Overpass fallback for any area

## Architecture

```
  +-------- Browser (Vue 3 / Leaflet) --------+
  |  RoutePanel     MapViewer                 |
  |  TelemetrySidebar   Traffic               |
  |  AboutSlider                              |
  +--------------------+----------------------+
                       |
  +--------------------v----------------------+
  |  FastAPI (Uvicorn)                        |
  |  POST /api/route                          |
  |  POST /api/traffic                        |
  |  POST /api/contact                        |
  |  GET  /static/* (SPA)                     |
  |  +-- Algorithms -----------------------+  |
  |  | Dijkstra    A*                      |  |
  |  | Bi-Directional    Greedy            |  |
  |  | heapq  O((V+E) log V)              |  |
  |  +-----------------+-------------------+  |
  |                    |                       |
  |  +-----------------v-------------------+  |
  |  | Overpass API (fallback)             |  |
  |  +-------------------------------------+  |
  +--------------------------------------------+
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 (Composition API), Vite 6, Tailwind CSS v4, Leaflet 1.9 |
| Backend | FastAPI, Uvicorn, httpx, python-dotenv |
| Algorithms | Pure Python with `heapq` — O((V+E) log V) |
| Data | OpenStreetMap via Overpass API (dynamic) + static Mersin graph |
| Email | Resend API |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env   # edit with your Resend key
uvicorn main:app --reload
```

### Frontend (Development)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

### Environment Variables

Create `backend/.env`:

```
ENV=development
RESEND_API_KEY=re_xxxx              # Resend API key (for contact form)
MAIL_FROM_ADDRESS=no-reply@your.domain
```

## Production

```bash
cd frontend
npm run build
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The compiled SPA is served from `static/` alongside the API on the same port.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/route` | Compute route `{start_lat, start_lng, end_lat, end_lng, algorithm}` |
| POST | `/api/traffic` | Update edge weight `{area_key, edge_from, edge_to, new_weight}` |
| POST | `/api/contact` | Send contact email `{name, email, message}` |
| GET | `/static/*` | Served SPA (production only) |

All requests/responses use Pydantic-validated JSON schemas. 50 km maximum distance enforced on both frontend and backend.

## Project Structure

```
├── backend/
│   ├── main.py            # FastAPI app, endpoints, SPA catch-all
│   ├── algorithms.py      # Dijkstra, A*, Bi-D, Greedy engines
│   ├── graph_loader.py    # In-memory graph cache, Overpass fetch
│   └── schemas.py         # Pydantic request/response models
├── frontend/
│   ├── src/
│   │   ├── App.vue        # Root layout, state management
│   │   ├── components/
│   │   │   ├── MapViewer.vue        # Leaflet map + animation
│   │   │   ├── RoutePanel.vue       # Coordinate display + actions
│   │   │   ├── TelemetrySidebar.vue # Diagnostics + playback
│   │   │   ├── MobilePlaybackBar.vue# Mobile playback controls
│   │   │   ├── AboutSlider.vue      # 5-tab academic docs
│   │   │   ├── TrafficPanel.vue     # Traffic mode toggle
│   │   │   └── AlgoSelector.vue     # Algorithm pill selector
│   │   └── main.js
│   └── package.json
├── scripts/
│   └── fetch_mersin.py    # One-time Overpass fetch for Mersin
├── static/                # Built SPA (generated)
└── requirements.txt
```
