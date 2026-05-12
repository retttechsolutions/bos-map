/**
 * MapController: wraps MapLibre GL JS and manages ILS map layers.
 * Emits events when user clicks an ILS area or hovers over one.
 */

import maplibregl from 'maplibre-gl'
import type { ILSFeature, ILSFeatureCollection } from '../types/ils'
import {
  SOURCE_ILS_POLYGONS,
  SOURCE_ILS_POINTS,
  LAYER_FILL,
  LAYER_OUTLINE,
  LAYER_HOVER,
  LAYER_SELECTED,
  LAYER_SELECTED_OUTLINE,
  LAYER_POINTS,
  LAYER_LABELS,
} from './layers'

export type ILSClickHandler = (feature: ILSFeature) => void

export class MapController {
  private map: maplibregl.Map
  private hoveredId: string | number | null = null
  private selectedId: string | number | null = null
  private polygonsLoaded = false

  constructor(containerId: string) {
    this.map = new maplibregl.Map({
      container: containerId,
      style: {
        version: 8,
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxzoom: 19,
          },
        },
        layers: [
          { id: 'osm', type: 'raster', source: 'osm-tiles' },
        ],
      },
      center: [10.45, 51.1],  // Germany center
      zoom: 6,
      minZoom: 4,
      maxZoom: 18,
    })

    this.map.addControl(new maplibregl.NavigationControl(), 'top-right')
    this.map.addControl(
      new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true } }),
      'top-right',
    )
    this.map.addControl(new maplibregl.ScaleControl(), 'bottom-left')
  }

  get instance(): maplibregl.Map {
    return this.map
  }

  /** Load centroid points layer immediately (lightweight). */
  async loadPoints(geojsonUrl: string): Promise<void> {
    const response = await fetch(geojsonUrl)
    const data = await response.json() as ILSFeatureCollection

    await new Promise<void>(resolve => {
      if (this.map.isStyleLoaded()) { resolve(); return }
      this.map.once('load', () => resolve())
    })

    this.map.addSource(SOURCE_ILS_POINTS, { type: 'geojson', data })
    this.map.addLayer(LAYER_POINTS)
    this.map.addLayer(LAYER_LABELS)
  }

  /** Load full polygon layer (heavier, loaded on demand). */
  async loadPolygons(geojsonUrl: string, onClickILS: ILSClickHandler): Promise<void> {
    if (this.polygonsLoaded) return
    this.polygonsLoaded = true

    const response = await fetch(geojsonUrl)
    const data = await response.json() as ILSFeatureCollection

    // Insert polygon layers below point layer
    const beforeLayer = this.map.getLayer(SOURCE_ILS_POINTS) ? SOURCE_ILS_POINTS : undefined

    this.map.addSource(SOURCE_ILS_POLYGONS, {
      type: 'geojson',
      data,
      generateId: true,  // needed for feature-state
    })
    this.map.addLayer(LAYER_FILL, beforeLayer)
    this.map.addLayer(LAYER_OUTLINE, beforeLayer)
    this.map.addLayer(LAYER_HOVER, beforeLayer)
    this.map.addLayer(LAYER_SELECTED, beforeLayer)
    this.map.addLayer(LAYER_SELECTED_OUTLINE, beforeLayer)

    // Hover interaction
    this.map.on('mousemove', 'ils-fill', e => {
      if (!e.features?.length) return
      const id = e.features[0].id
      if (this.hoveredId !== null && this.hoveredId !== id) {
        this.map.setFeatureState({ source: SOURCE_ILS_POLYGONS, id: this.hoveredId }, { hover: false })
      }
      this.hoveredId = id ?? null
      if (id !== undefined) {
        this.map.setFeatureState({ source: SOURCE_ILS_POLYGONS, id }, { hover: true })
      }
      this.map.getCanvas().style.cursor = 'pointer'
    })

    this.map.on('mouseleave', 'ils-fill', () => {
      if (this.hoveredId !== null) {
        this.map.setFeatureState({ source: SOURCE_ILS_POLYGONS, id: this.hoveredId }, { hover: false })
        this.hoveredId = null
      }
      this.map.getCanvas().style.cursor = ''
    })

    // Click interaction
    this.map.on('click', 'ils-fill', e => {
      if (!e.features?.length) return
      const raw = e.features[0]
      this._selectFeature(raw.id ?? null)
      onClickILS(raw as unknown as ILSFeature)
    })
  }

  private _selectFeature(id: string | number | null): void {
    if (this.selectedId !== null) {
      this.map.setFeatureState(
        { source: SOURCE_ILS_POLYGONS, id: this.selectedId },
        { selected: false },
      )
    }
    this.selectedId = id
    if (id !== null) {
      this.map.setFeatureState(
        { source: SOURCE_ILS_POLYGONS, id },
        { selected: true },
      )
    }
  }

  /** Fly the camera to a coordinate and optionally select the ILS there. */
  flyTo(lng: number, lat: number, zoom = 10): void {
    this.map.flyTo({ center: [lng, lat], zoom, speed: 1.5 })
  }

  /** Clean up the map instance. */
  destroy(): void {
    this.map.remove()
  }
}
