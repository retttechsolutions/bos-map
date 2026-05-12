/**
 * InfoPanel: slide-in side panel displaying ILS details.
 * Renders Leitstellen properties including Funkgruppen.
 */

import type { ILSFeature, ILSProperties } from '../types/ils'
import { BL_NAMES, BL_COLORS } from '../types/ils'

export class InfoPanel {
  private el: HTMLElement

  constructor(containerId: string) {
    const existing = document.getElementById(containerId)
    if (!existing) throw new Error(`InfoPanel container #${containerId} not found`)
    this.el = existing
    this.el.classList.add('info-panel', 'info-panel--hidden')
  }

  show(feature: ILSFeature): void {
    this.el.innerHTML = this._render(feature.properties)
    this.el.classList.remove('info-panel--hidden')
    this.el.querySelector('.info-panel__close')?.addEventListener('click', () => this.hide())
  }

  hide(): void {
    this.el.classList.add('info-panel--hidden')
  }

  private _render(p: ILSProperties): string {
    const blName = BL_NAMES[p.bundesland] ?? p.bundesland
    const blColor = BL_COLORS[p.bundesland] ?? '#888'
    const reviewBadge = this._reviewBadge(p.review_status)
    const osmLink = p.adresse
      ? `<a href="https://www.openstreetmap.org/search?query=${encodeURIComponent(p.adresse)}" target="_blank" rel="noopener">OSM</a>`
      : ''
    const apiLink = `<a href="/api/v1/${p.leitstellen_id}.json" target="_blank" rel="noopener">JSON</a>`
    const funkgruppenHtml = this._renderFunkgruppen(p)

    return `
      <div class="info-panel__header" style="border-left: 4px solid ${blColor}">
        <h2 class="info-panel__name">${this._esc(p.leitstellenname)}</h2>
        <button class="info-panel__close" aria-label="Schließen">✕</button>
      </div>
      <div class="info-panel__body">
        <span class="badge" style="background:${blColor}">${blName}</span>
        ${reviewBadge}

        <dl class="info-panel__dl">
          <dt>ID</dt><dd><code>${this._esc(p.leitstellen_id)}</code></dd>
          ${p.traeger ? `<dt>Träger</dt><dd>${this._esc(p.traeger)}</dd>` : ''}
          ${p.betreiber ? `<dt>Betreiber</dt><dd>${this._esc(p.betreiber)}</dd>` : ''}
          ${p.adresse ? `<dt>Adresse</dt><dd>${this._esc(p.adresse)}</dd>` : ''}
          ${p.telefon ? `<dt>Telefon</dt><dd><a href="tel:${this._esc(p.telefon)}">${this._esc(p.telefon)}</a></dd>` : ''}
          <dt>Geodatenquelle</dt><dd>${this._esc(p.quelltyp)}</dd>
          <dt>Geometrie</dt><dd>${this._esc(p.geometry_basis)}</dd>
          <dt>Gültig ab</dt><dd>${this._esc(p.valid_from)}</dd>
        </dl>

        ${funkgruppenHtml}

        <div class="info-panel__links">
          ${p.source_url ? `<a href="${this._esc(p.source_url)}" target="_blank" rel="noopener">Datenquelle</a>` : ''}
          ${osmLink}
          ${apiLink}
        </div>

        ${p.bemerkung ? `<p class="info-panel__note">${this._esc(p.bemerkung)}</p>` : ''}
      </div>
    `
  }

  private _renderFunkgruppen(p: ILSProperties): string {
    if (!p.funkgruppen?.length) {
      return '<p class="info-panel__no-data">Keine Funkgruppen erfasst</p>'
    }
    const rows = p.funkgruppen.map(fg => `
      <tr>
        <td><code>${this._esc(fg.name)}</code></td>
        <td>${this._esc(fg.rolle)}</td>
        <td>${fg.kurzwahl ? this._esc(fg.kurzwahl) : '–'}</td>
        <td><small>${this._esc(fg.quelle)}</small></td>
      </tr>
    `).join('')
    return `
      <h3 class="info-panel__section-title">Funkgruppen</h3>
      <table class="funkgruppen-table">
        <thead><tr><th>Name</th><th>Rolle</th><th>Kurzwahl</th><th>Quelle</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `
  }

  private _reviewBadge(status: string): string {
    const labels: Record<string, [string, string]> = {
      verified: ['Verifiziert', '#2a9d8f'],
      needs_review: ['Prüfung ausstehend', '#e9c46a'],
      community: ['Community', '#adb5bd'],
    }
    const [label, color] = labels[status] ?? ['Unbekannt', '#888']
    return `<span class="badge" style="background:${color}">${label}</span>`
  }

  private _esc(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }
}
