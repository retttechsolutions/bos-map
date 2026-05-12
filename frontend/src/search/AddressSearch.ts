/**
 * AddressSearch: Nominatim-backed address/place search.
 * Debounces input, restricts results to Germany, and returns [lng, lat].
 */

export interface SearchResult {
  displayName: string
  lng: number
  lat: number
  bbox: [number, number, number, number] | null  // [minLon, minLat, maxLon, maxLat]
}

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
const DEBOUNCE_MS = 350

export class AddressSearch {
  private debounceTimer: ReturnType<typeof setTimeout> | null = null
  private abortController: AbortController | null = null
  private onResult: (results: SearchResult[]) => void

  constructor(onResult: (results: SearchResult[]) => void) {
    this.onResult = onResult
  }

  /** Queue a search for *query*. Previous pending request is cancelled. */
  search(query: string): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer)
    if (!query.trim()) {
      this.onResult([])
      return
    }
    this.debounceTimer = setTimeout(() => this._fetch(query.trim()), DEBOUNCE_MS)
  }

  private async _fetch(query: string): Promise<void> {
    this.abortController?.abort()
    this.abortController = new AbortController()

    try {
      const params = new URLSearchParams({
        q: query,
        countrycodes: 'de',
        format: 'geojson',
        limit: '5',
        addressdetails: '0',
      })
      const resp = await fetch(`${NOMINATIM_URL}?${params}`, {
        signal: this.abortController.signal,
        headers: { 'Accept-Language': 'de' },
      })
      if (!resp.ok) return

      const data = await resp.json()
      const results: SearchResult[] = (data.features ?? []).map((feat: GeoJSON.Feature) => {
        const [lng, lat] = (feat.geometry as GeoJSON.Point).coordinates
        const props = feat.properties as Record<string, unknown>
        const bb = props.boundingbox as string[] | undefined
        const bbox: [number, number, number, number] | null = bb
          ? [parseFloat(bb[2]), parseFloat(bb[0]), parseFloat(bb[3]), parseFloat(bb[1])]
          : null
        return {
          displayName: String(props.display_name ?? ''),
          lng,
          lat,
          bbox,
        }
      })
      this.onResult(results)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.warn('Nominatim search error:', err)
        this.onResult([])
      }
    }
  }

  /** Cancel any pending request. */
  cancel(): void {
    this.abortController?.abort()
    if (this.debounceTimer) clearTimeout(this.debounceTimer)
  }
}
