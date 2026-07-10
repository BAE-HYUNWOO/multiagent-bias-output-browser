import type { ContextVariant, ProblemVariant } from '../types'
import { variantLabel } from '../lib/labels'

function AnswerBadge({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <span className="answer-meta-badge">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  )
}

interface QuestionPanelProps {
  variant: ProblemVariant
  availableVariants: ContextVariant[]
  selectedVariant: ContextVariant
  onVariantChange: (variant: ContextVariant) => void
}

export default function QuestionPanel({
  variant,
  availableVariants,
  selectedVariant,
  onVariantChange,
}: QuestionPanelProps) {
  const options = Object.entries(variant.options).filter(([, value]) => value)

  return (
    <section className="question-panel">
      <div className="section-heading question-panel-title">
        <h2>Problem</h2>
      </div>

      <div className="question-panel-controls">
        <div className="variant-toggle question-variant-toggle" aria-label="Context type">
          {availableVariants.map((contextVariant) => (
            <button
              type="button"
              key={contextVariant}
              className={selectedVariant === contextVariant ? 'active' : ''}
              onClick={() => onVariantChange(contextVariant)}
            >
              {variantLabel(contextVariant)}
            </button>
          ))}
        </div>
      </div>

      <div className="question-block">
        <h3>Context</h3>
        <p>{variant.context || '—'}</p>
      </div>
      <div className="question-block">
        <h3>Question</h3>
        <p>{variant.question || '—'}</p>
      </div>
      <div className="option-list">
        {options.map(([key, value]) => (
          <div className="option-row" key={key}>
            <strong>{key}</strong>
            <span>{value}</span>
          </div>
        ))}
      </div>
      <div className="answer-meta-row">
        <AnswerBadge label="Correct" value={variant.correct_answer} />
        <AnswerBadge label="Stereotype" value={variant.stereotype_answer} />
        <AnswerBadge label="Anti-stereotype" value={variant.anti_stereotype_answer} />
      </div>
    </section>
  )
}
