/**
 * BOS-Map main entry point.
 *
 * Bootstrap order:
 * 1. Initialize map
 * 2. Load centroid points (lightweight, immediate)
 * 3. Load spatial index + polygon data (async, on demand)
 * 4. Wire up address search and map click handler
 */

import 'maplibre-gl/dist/maplibre-gl.css'
import { MapController } from './map/MapController'
import { SpatialIndex } from './query/SpatialIndex'
import { AddressSearch } from './search/AddressSearch'
import { InfoPanel } from './ui/InfoPanel'
import type { ILSFeature } from './types/ils'

const DATA_BASE = import.meta.env.BASE_URL

const mapCtrl = new MapController('map')
const spatialIndex = new SpatialIndex()
const infoPanel = new InfoPanel('info-panel')

// ── Load points immediately ──────────────────────────────────────────────────
mapCtrl.loadPoints(`${DATA_BASE}data/ils-points.geojson`).catch(console.error)

// ── Load polygons + spatial index lazily (on first interaction) ─────────────
let polygonsLoading = false

async function ensurePolygonsLoaded(): Promise<void> {
  if (spatialIndex.isReady || polygonsLoading) return
  polygonsLoading = true

  await Promise.all([
    spatialIndex.load(
      `${DATA_BASE}data/ils-index.json`,
      `${DATA_BASE}data/ils.geojson`,
    ),
    mapCtrl.loadPolygons(
      `${DATA_BASE}data/ils.geojson`,
      handleILSClick,
    ),
  ])
}

// ── ILS click handler ────────────────────────────────────────────────────────
function handleILSClick(feature: ILSFeature): void {
  infoPanel.show(feature)
}

// ── Map click (coordinates) → lookup ─────────────────────────────────────────
mapCtrl.instance.on('click', async e => {
  await ensurePolygonsLoaded()
  const { lng, lat } = e.lngLat
  const found = spatialIndex.lookup(lng, lat)
  if (found) {
    handleILSClick(found)
  } else {
    infoPanel.hide()
  }
})

// Load polygons on first zoom/pan to ensure hover is wired up
mapCtrl.instance.once('movestart', () => ensurePolygonsLoaded().catch(console.error))

// ── Address search ───────────────────────────────────────────────────────────
const searchInput = document.getElementById('search-input') as HTMLInputElement | null
const searchResults = document.getElementById('search-results') as HTMLElement | null

const addressSearch = new AddressSearch(results => {
  if (!searchResults) return
  searchResults.innerHTML = ''
  if (!results.length) {
    searchResults.hidden = true
    return
  }
  searchResults.hidden = false
  for (const result of results) {
    const li = document.createElement('li')
    li.textContent = result.displayName
    li.addEventListener('click', async () => {
      searchResults.hidden = true
      if (searchInput) searchInput.value = result.displayName
      mapCtrl.flyTo(result.lng, result.lat, 11)
      await ensurePolygonsLoaded()
      // Short delay to let map settle before lookup
      setTimeout(async () => {
        const found = spatialIndex.lookup(result.lng, result.lat)
        if (found) handleILSClick(found)
      }, 600)
    })
    searchResults.appendChild(li)
  }
})

searchInput?.addEventListener('input', e => {
  addressSearch.search((e.target as HTMLInputElement).value)
})

searchInput?.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    searchResults && (searchResults.hidden = true)
    addressSearch.cancel()
  }
})

// Close dropdown when clicking outside
document.addEventListener('click', e => {
  if (searchResults && !searchResults.contains(e.target as Node) && e.target !== searchInput) {
    searchResults.hidden = true
  }
})
