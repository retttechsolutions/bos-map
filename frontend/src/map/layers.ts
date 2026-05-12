/** MapLibre GL layer definitions for BOS-Map. */

import type { LayerSpecification, ExpressionSpecification } from 'maplibre-gl'
import { BL_COLORS } from '../types/ils'

// Build a MapLibre match expression for Bundesland → color
function blColorExpression(): ExpressionSpecification {
  const expr: unknown[] = ['match', ['get', 'bundesland']]
  for (const [bl, color] of Object.entries(BL_COLORS)) {
    expr.push(bl, color)
  }
  expr.push('#888888') // default fallback
  return expr as maplibregl.ExpressionSpecification
}

export const SOURCE_ILS_POLYGONS = 'ils-polygons'
export const SOURCE_ILS_POINTS = 'ils-points'

export const LAYER_FILL: LayerSpecification = {
  id: 'ils-fill',
  type: 'fill',
  source: SOURCE_ILS_POLYGONS,
  paint: {
    'fill-color': blColorExpression(),
    'fill-opacity': 0.15,
  },
}

export const LAYER_OUTLINE: LayerSpecification = {
  id: 'ils-outline',
  type: 'line',
  source: SOURCE_ILS_POLYGONS,
  paint: {
    'line-color': blColorExpression(),
    'line-width': 1.2,
    'line-opacity': 0.6,
  },
}

export const LAYER_HOVER: LayerSpecification = {
  id: 'ils-hover',
  type: 'fill',
  source: SOURCE_ILS_POLYGONS,
  paint: {
    'fill-color': blColorExpression(),
    'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.35, 0],
  },
}

export const LAYER_SELECTED: LayerSpecification = {
  id: 'ils-selected',
  type: 'fill',
  source: SOURCE_ILS_POLYGONS,
  paint: {
    'fill-color': blColorExpression(),
    'fill-opacity': ['case', ['boolean', ['feature-state', 'selected'], false], 0.5, 0],
  },
}

export const LAYER_SELECTED_OUTLINE: LayerSpecification = {
  id: 'ils-selected-outline',
  type: 'line',
  source: SOURCE_ILS_POLYGONS,
  paint: {
    'line-color': '#ffffff',
    'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 2.5, 0],
    'line-opacity': 1,
  },
}

export const LAYER_POINTS: LayerSpecification = {
  id: 'ils-points',
  type: 'circle',
  source: SOURCE_ILS_POINTS,
  paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3, 10, 6],
    'circle-color': blColorExpression(),
    'circle-stroke-color': '#ffffff',
    'circle-stroke-width': 1.5,
    'circle-opacity': 0.9,
  },
}

export const LAYER_LABELS: LayerSpecification = {
  id: 'ils-labels',
  type: 'symbol',
  source: SOURCE_ILS_POINTS,
  minzoom: 8,
  layout: {
    'text-field': ['get', 'leitstellenname'],
    'text-font': ['Open Sans Regular'],
    'text-size': 11,
    'text-offset': [0, 1.2],
    'text-anchor': 'top',
  },
  paint: {
    'text-color': '#1a1a1a',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1.5,
  },
}
