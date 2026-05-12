/** TypeScript types matching the canonical ILS GeoJSON feature schema. */

export type Bundesland =
  | 'BB' | 'BE' | 'BW' | 'BY' | 'HB' | 'HE' | 'HH'
  | 'MV' | 'NI' | 'NW' | 'RP' | 'SH' | 'SL' | 'SN' | 'ST' | 'TH'

export type Quelltyp =
  | 'amtlich_wfs' | 'amtlich_ogcapi' | 'amtlich_html'
  | 'recht_abgeleitet' | 'community'

export type GeometryBasis =
  | 'amtliche_grenze' | 'verwaltungsgrenze_abgeleitet' | 'digitalisiert' | 'community'

export type ReviewStatus = 'verified' | 'needs_review' | 'community'

export type FunkgruppenRolle =
  | 'Feuerwehr' | 'Rettungsdienst' | 'KatS' | 'Polizei' | 'THW'
  | 'Hilfsorganisation' | 'Pool' | 'DMO' | 'sonstige'

export interface Funkgruppe {
  name: string
  rolle: FunkgruppenRolle
  quelle: 'landeskonzept' | 'amtlich' | 'community'
  kurzwahl: string | null
}

export interface ILSProperties {
  leitstellen_id: string
  leitstellenname: string
  bundesland: Bundesland
  traeger: string | null
  betreiber: string | null
  adresse: string | null
  telefon: string | null
  notruf: string | null
  quelltyp: Quelltyp
  funkgruppen: Funkgruppe[]
  frequenzschema: string | null
  geometry_basis: GeometryBasis
  source_url: string | null
  source_crs: string | null
  valid_from: string
  valid_to: string | null
  review_status: ReviewStatus
  bemerkung: string | null
}

export interface ILSFeature {
  type: 'Feature'
  properties: ILSProperties
  geometry: GeoJSON.MultiPolygon | null
}

export interface ILSFeatureCollection {
  type: 'FeatureCollection'
  features: ILSFeature[]
}

/** Lightweight entry from api/v1/index.json */
export interface ILSIndexEntry {
  leitstellen_id: string
  leitstellenname: string | null
  bundesland: Bundesland
  traeger: string | null
  adresse: string | null
  review_status: ReviewStatus
  bbox: [number, number, number, number] | null // [minLon, minLat, maxLon, maxLat]
}

/** Entry in the spatial index (ils-index.json) */
export interface SpatialIndexEntry {
  minX: number
  minY: number
  maxX: number
  maxY: number
  index: number
}

export interface SpatialIndexFile {
  type: 'ILSSpatialIndex'
  version: number
  count: number
  entries: SpatialIndexEntry[]
}

// Bundesland display names
export const BL_NAMES: Record<Bundesland, string> = {
  BB: 'Brandenburg',
  BE: 'Berlin',
  BW: 'Baden-Württemberg',
  BY: 'Bayern',
  HB: 'Bremen',
  HE: 'Hessen',
  HH: 'Hamburg',
  MV: 'Mecklenburg-Vorpommern',
  NI: 'Niedersachsen',
  NW: 'Nordrhein-Westfalen',
  RP: 'Rheinland-Pfalz',
  SH: 'Schleswig-Holstein',
  SL: 'Saarland',
  SN: 'Sachsen',
  ST: 'Sachsen-Anhalt',
  TH: 'Thüringen',
}

// Color per Bundesland for map styling
export const BL_COLORS: Record<Bundesland, string> = {
  BB: '#e63946', BE: '#457b9d', BW: '#2a9d8f', BY: '#1d3557',
  HB: '#e9c46a', HE: '#f4a261', HH: '#264653', MV: '#6a4c93',
  NI: '#43aa8b', NW: '#f8961e', RP: '#577590', SH: '#4cc9f0',
  SL: '#f72585', SN: '#7209b7', ST: '#3a0ca3', TH: '#480ca8',
}
