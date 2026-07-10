import { stageLabel } from '../lib/labels'
import type { StageOutput } from '../types'

export default function AgentCard({
  stage,
  emphasis = false,
  previousAnswer,
}: {
  stage: StageOutput | null
  emphasis?: boolean
  previousAnswer?: string | null
}) {
  if (!stage) {
    return (
      <article className="agent-card missing-card">
        <span className="stage-name">Missing stage</span>
        <p>저장된 결과가 없습니다.</p>
      </article>
    )
  }

  const changed = previousAnswer != null && stage.answer != null && previousAnswer !== stage.answer

  return (
    <article className={`agent-card${emphasis ? ' final-card' : ''}`}>
      <div className="agent-card-top">
        <span className="stage-name">{stageLabel(stage.stage)}</span>
        <span
          className={`answer-pill ${
            stage.correct === true ? 'correct' : stage.correct === false ? 'incorrect' : ''
          }`}
        >
          {previousAnswer != null ? `${previousAnswer ?? '—'} → ${stage.answer ?? '—'}` : stage.answer ?? '—'}
        </span>
      </div>
      {changed ? <span className="change-chip">Changed</span> : previousAnswer != null ? <span className="change-chip muted">Unchanged</span> : null}
      <p className="reason-text">{stage.reason || 'Reason이 저장되지 않았습니다.'}</p>
      {(stage.prompt_tokens != null || stage.completion_tokens != null) && (
        <div className="usage-row">
          <span>Input {stage.prompt_tokens ?? '—'}</span>
          <span>Output {stage.completion_tokens ?? '—'}</span>
          {stage.total_cost_usd != null ? <span>${stage.total_cost_usd.toFixed(6)}</span> : null}
        </div>
      )}
    </article>
  )
}
