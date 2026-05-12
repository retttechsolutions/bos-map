/**
 * SpatialIndex: loads the pre-built spatial index and ILS polygon data,
 * provides fast point-in-polygon lookups using rbush + turf.
 */

import RBush from 'rbush'
import { booleanPointInPolygon } from '@turf/boolean-point-in-polygon'
import { point as turfPoint } from '@turf/helpers'
import type { ILSFeature, ILSFeatureCollection, SpatialIndexFile } from '../types/ils'

interface RBushItem {
  minX: number
  minY: number
  maxX: number
  maxY: number
  index: number
}

export class SpatialIndex {
  private tree = new RBush<RBushItem>()
  private features: ILSFeature[] = []
  private ready = false

  async load(indexUrl: string, geojsonUrl: string): Promise<void> {
    const [indexData, geojsonData] = await Promise.all([
      fetch(indexUrl).then(r => r.json()) as Promise<SpatialIndexFile>,
      fetch(geojsonUrl).then(r => r.json()) as Promise<ILSFeatureCollection>,
    ])

    this.features = geojsonData.features
    this.tree.load(indexData.entries)
    this.ready = true
  }

  /** Returns the ILS feature containing [lng, lat], or null if none. */
  lookup(lng: number, lat: number): ILSFeature | null {
    if (!this.ready) return null

    const pt = turfPoint([lng, lat])

    // Phase 1: fast bbox pre-filter (O(log n))
    const candidates = this.tree.search({ minX: lng, minY: lat, maxX: lng, maxY: lat })

    // Phase 2: exact point-in-polygon test on candidates only
    for (const candidate of candidates) {
      const feature = this.features[candidate.index]
      if (!feature?.geometry) continue
      try {
        if (booleanPointInPolygon(pt, feature as unknown as GeoJSON.Feature<GeoJSON.MultiPolygon>)) {
          return feature
        }
      } catch {
        // malformed geometry – skip
      }
    }
    return null
  }

  get isReady(): boolean {
    return this.ready
  }

  get featureCount(): number {
    return this.features.length
  }
}
