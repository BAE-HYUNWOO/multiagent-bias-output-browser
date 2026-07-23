import { useEffect, useMemo, useState } from 'react'
import { ErrorView, LoadingView } from '../components/StatusView'
import { loadExperimentManifest, loadPromptExamples, withBase } from '../lib/data'
import { modelLabel } from '../lib/labels'
import type {
  ExperimentManifest,
  PromptExampleCard,
  PromptExamplesData,
} from '../types'

const GROUPS = [
  {
    id: 'single',
    label: 'Single Agent',
    description: 'The direct single-agent request used in the main experiment.',
  },
  {
    id: 'multi_agent',
    label: 'Multi-Agent Flow',
    description: 'Round 1, judge, revision, and final judge prompts actually used in Run 1.',
  },
  {
    id: 'neutral_agent',
    label: 'Neutral Agent Ablation',
    description: 'The Neutral Agent prompts replacing the Sufficiency Agent role.',
  },
] as const

function PromptCard({ card }: { card: PromptExampleCard }) {
  return (
    <article className="prompt-example-card">
      <div className="prompt-card-header">
        <div>
          <span className="prompt-stage-code">{card.stage}</span>
          <h3>{card.label}</h3>
        </div>
        <span className="prompt-experiment-badge">{card.experiment}</span>
      </div>

      <div className="prompt-section">
        <strong>System prompt</strong>
        <pre>{card.system_prompt}</pre>
      </div>

      <div className="prompt-section actual-prompt">
        <strong>Actually sent user prompt</strong>
        <pre>{card.user_prompt}</pre>
      </div>

      <div className="prompt-section prompt-output">
        <strong>Actual parsed output</strong>
        <pre>{JSON.stringify(card.actual_output, null, 2)}</pre>
      </div>
    </article>
  )
}

export default function PromptExamplesPage() {
  const [data, setData] = useState<PromptExamplesData | null>(null)
  const [manifest, setManifest] = useState<ExperimentManifest | null>(null)
  const [languageCode, setLanguageCode] = useState('en')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([loadPromptExamples(), loadExperimentManifest()])
      .then(([promptData, experimentManifest]) => {
        setData(promptData)
        setManifest(experimentManifest)
        setLanguageCode(promptData.languages[0]?.language_code ?? 'en')
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      )
  }, [])

  const selectedLanguage = useMemo(
    () => data?.languages.find((item) => item.language_code === languageCode) ?? null,
    [data, languageCode],
  )

  if (error) return <ErrorView message={error} />
  if (!data || !manifest || !selectedLanguage) return <LoadingView />

  return (
    <div className="page-content prompt-examples-page">
      <section className="prompt-page-heading">
        <div>
          <span className="eyebrow">Recorded API inputs</span>
          <h1>Prompt Examples</h1>
          <p>
            Actual system prompts, user prompts, and parsed outputs recorded for{' '}
            {modelLabel(data.model)}.
          </p>
        </div>
        {manifest.prompt_examples_download ? (
          <a
            className="secondary-button"
            href={withBase(manifest.prompt_examples_download)}
            download
          >
            Download Prompt Files
          </a>
        ) : null}
      </section>

      <section className="prompt-language-tabs" aria-label="Prompt language">
        {data.languages.map((language) => (
          <button
            type="button"
            key={language.language_code}
            className={language.language_code === languageCode ? 'active' : ''}
            onClick={() => setLanguageCode(language.language_code)}
          >
            <strong>{language.dataset}</strong>
            <span>{language.language}</span>
          </button>
        ))}
      </section>

      <section className="prompt-item-context">
        <div>
          <span>Item</span>
          <strong>{selectedLanguage.item.item_id}</strong>
        </div>
        <div>
          <span>Category</span>
          <strong>{selectedLanguage.item.category}</strong>
        </div>
        <div>
          <span>Context type</span>
          <strong>{selectedLanguage.item.context_type}</strong>
        </div>
        <div>
          <span>Model</span>
          <strong>{modelLabel(selectedLanguage.model)}</strong>
        </div>
      </section>

      {GROUPS.map((group) => {
        const cards = selectedLanguage.cards.filter((card) => card.group === group.id)
        if (!cards.length) return null
        return (
          <section className="prompt-group" key={group.id}>
            <div className="prompt-group-heading">
              <h2>{group.label}</h2>
              <p>{group.description}</p>
            </div>
            <div className="prompt-card-grid">
              {cards.map((card) => (
                <PromptCard key={`${card.group}-${card.stage}`} card={card} />
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
