import { useEffect, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { loadDownloadManifest, loadSiteConfig, withBase } from '../lib/data'
import type { DownloadManifest, SiteConfig } from '../types'

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const isProblemPage = location.pathname.includes('/problem/')

  const problemHeaderPath = (() => {
    if (!isProblemPage) return null
    const parts = location.pathname.split('/').filter(Boolean)
    const datasetIndex = parts.indexOf('dataset')
    const categoryIndex = parts.indexOf('category')
    if (datasetIndex < 0 || categoryIndex < 0) return null

    const dataset = (parts[datasetIndex + 1] ?? '').toUpperCase()
    const categorySlug = parts[categoryIndex + 1] ?? ''
    const category = categorySlug
      .split('-')
      .filter(Boolean)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')

    return { dataset, category }
  })()
  const [config, setConfig] = useState<SiteConfig>({
    title: 'Multi-Agent Bias Output Browser',
    subtitle: 'BBQ · CBBQ · KoBBQ datasets and model outputs',
  })
  const [manifest, setManifest] = useState<DownloadManifest | null>(null)

  useEffect(() => {
    loadSiteConfig().then(setConfig).catch(() => undefined)
    loadDownloadManifest().then(setManifest).catch(() => undefined)
  }, [])

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to="/">
            <span className="brand-mark">MA</span>
            <span className="brand-copy">
              <strong>{config.title}</strong>
            </span>
          </Link>
          {problemHeaderPath ? (
            <div className="header-actions">
              <nav className="header-context-path" aria-label="Current location">
                <span>{problemHeaderPath.dataset}</span>
                <b aria-hidden="true">›</b>
                <span>{problemHeaderPath.category}</span>
                <b aria-hidden="true">›</b>
                <strong>Problem</strong>
              </nav>
              <Link className="header-home-button" to="/">Home</Link>
            </div>
          ) : manifest?.all_processed ? (
            <a className="header-download-button" href={withBase(manifest.all_processed)} download>
              Download
            </a>
          ) : null}
        </div>
      </header>
      <main className="page-shell">{children}</main>
      <footer className="site-footer">
        Dataset questions and recorded model outputs are displayed without rerunning the models.
      </footer>
    </div>
  )
}
