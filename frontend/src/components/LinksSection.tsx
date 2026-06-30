import { LinkedIn, GitHub, Globe } from './Icons'
import type { DiscoveredUrls } from '../api/types'

interface LinksSectionProps {
  urls: DiscoveredUrls | null
  enrichmentStatus: string
}

export function LinksSection({ urls, enrichmentStatus }: LinksSectionProps) {
  if (!urls || (!urls.linkedin && !urls.github && !urls.portfolio)) {
    return <div className="section-empty">No profile links discovered</div>
  }

  return (
    <div className="links-grid">
      {urls.linkedin && (
        <a href={urls.linkedin} target="_blank" rel="noopener noreferrer" className="link-card linkedin">
          <span className="link-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <LinkedIn size={20} />
          </span>
          <div>
            <span className="link-label">LinkedIn</span>
            <span className="link-url">{urls.linkedin.replace('https://', '')}</span>
          </div>
          {enrichmentStatus === 'completed' && <span className="link-enriched" title="Enriched via APIFY">✓ Enriched</span>}
        </a>
      )}
      {urls.github && (
        <a href={urls.github} target="_blank" rel="noopener noreferrer" className="link-card github">
          <span className="link-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <GitHub size={20} />
          </span>
          <div>
            <span className="link-label">GitHub</span>
            <span className="link-url">{urls.github.replace('https://', '')}</span>
          </div>
          {enrichmentStatus === 'completed' && <span className="link-enriched" title="Enriched via APIFY">✓ Enriched</span>}
        </a>
      )}
      {urls.portfolio && (
        <a href={urls.portfolio} target="_blank" rel="noopener noreferrer" className="link-card portfolio">
          <span className="link-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <Globe size={20} />
          </span>
          <div>
            <span className="link-label">Portfolio</span>
            <span className="link-url">{urls.portfolio.replace('https://', '')}</span>
          </div>
        </a>
      )}
    </div>
  )
}
