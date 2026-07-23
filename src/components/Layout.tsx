import { useEffect, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { loadSiteConfig } from '../lib/data'
import type { SiteConfig } from '../types'

const EXPERIMENT_LINKS = [
  { id: 'main', label: 'Main Experiment', to: '/?experiment=main' },
  {
    id: 'neutral_agent_ablation',
    label: 'Neutral Agent Ablation',
    to: '/?experiment=neutral_agent_ablation',
  },
  {
    id: 'sufficiency_repeatability',
    label: 'Sufficiency Repeatability',
    to: '/?experiment=sufficiency_repeatability&run=1',
  },
  { id: 'prompt_examples', label: 'Prompt Examples', to: '/prompts' },
] as const

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const query = new URLSearchParams(location.search)
  const experimentId =
    location.pathname === '/prompts'
      ? 'prompt_examples'
      : query.get('experiment') ?? 'main'
  const [config, setConfig] = useState<SiteConfig>({
    title: 'Multi-Agent Bias Output Browser',
    subtitle: 'BBQ · CBBQ · KoBBQ datasets and model outputs',
  })

  useEffect(() => {
    loadSiteConfig().then(setConfig).catch(() => undefined)
  }, [])

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to="/?experiment=main">
            <span className="brand-mark">MA</span>
            <span className="brand-copy">
              <strong>{config.title}</strong>
            </span>
          </Link>
          <nav className="experiment-header-nav" aria-label="Experiment views">
            {EXPERIMENT_LINKS.map((item) => (
              <Link
                key={item.id}
                className={experimentId === item.id ? 'active' : ''}
                to={item.to}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="page-shell">{children}</main>
      <footer className="site-footer">
        Dataset questions and recorded model outputs are displayed without rerunning the models.
      </footer>
    </div>
  )
}
