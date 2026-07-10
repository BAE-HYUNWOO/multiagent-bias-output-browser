import { useMemo } from 'react'
import type { ModelResult, StageOutput } from '../types'
import { modelLabel } from '../lib/labels'
import AgentCard from './AgentCard'

const CONDITIONS = [
  { id: 'single', label: 'Single Agent' },
  { id: 'no_revision', label: 'Multi-Agent Without Revision' },
  { id: 'with_revision', label: 'Multi-Agent With Revision' },
] as const

export type ConditionId = (typeof CONDITIONS)[number]['id']

function stageByName(stages: StageOutput[], name: string): StageOutput | null {
  return stages.find((stage) => stage.stage === name) ?? null
}

function RoundGrid({ stages }: { stages: StageOutput[] }) {
  return (
    <div className="agent-grid three-columns">
      <AgentCard stage={stageByName(stages, 'context_agent_r1')} />
      <AgentCard stage={stageByName(stages, 'option_agent_r1')} />
      <AgentCard stage={stageByName(stages, 'sufficiency_agent_r1')} />
    </div>
  )
}

interface ConditionViewerProps {
  result: ModelResult
  models: string[]
  model: string
  onModelChange: (model: string) => void
  condition: ConditionId
  onConditionChange: (condition: ConditionId) => void
}

export default function ConditionViewer({
  result,
  models,
  model,
  onModelChange,
  condition,
  onConditionChange,
}: ConditionViewerProps) {

  const revisionPairs = useMemo(
    () => [
      ['context_agent_r1', 'context_agent_r2'],
      ['option_agent_r1', 'option_agent_r2'],
      ['sufficiency_agent_r1', 'sufficiency_agent_r2'],
    ],
    [],
  )

  return (
    <section className="results-panel">
      <div className="section-heading result-panel-heading">
        <div>
          <h2>Agent Result Flow</h2>
        </div>
        <div className="filter-control result-model-control">
          <label htmlFor="model-select">Model</label>
          <select
            id="model-select"
            value={model}
            onChange={(event) => onModelChange(event.target.value)}
          >
            {models.map((item) => (
              <option key={item} value={item}>{modelLabel(item)}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="condition-tabs" role="tablist">
        {CONDITIONS.map((item) => (
          <button
            key={item.id}
            className={condition === item.id ? 'active' : ''}
            onClick={() => onConditionChange(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {condition === 'single' ? (
        <div className="single-result-wrap">
          <AgentCard stage={result.single_agent.final} emphasis />
        </div>
      ) : null}

      {condition === 'no_revision' ? (
        <div className="flow-stack">
          <div className="flow-label">Round 1</div>
          <RoundGrid stages={result.multi_agent_no_revision.stages} />
          <div className="flow-arrow">↓</div>
          <div className="final-result-wrap">
            <AgentCard stage={result.multi_agent_no_revision.final} emphasis />
          </div>
        </div>
      ) : null}

      {condition === 'with_revision' ? (
        <div className="flow-stack">
          <div className="flow-label">Round 1</div>
          <RoundGrid stages={result.multi_agent_with_revision.stages} />
          <div className="flow-arrow">↓</div>
          <div className="flow-label">Revision Round</div>
          <div className="agent-grid three-columns">
            {revisionPairs.map(([r1, r2]) => {
              const before = stageByName(result.multi_agent_with_revision.stages, r1)
              const after = stageByName(result.multi_agent_with_revision.stages, r2)
              return (
                <AgentCard
                  key={r2}
                  stage={after}
                  previousAnswer={before?.answer ?? null}
                />
              )
            })}
          </div>
          <div className="flow-arrow">↓</div>
          <div className="final-result-wrap">
            <AgentCard stage={result.multi_agent_with_revision.final} emphasis />
          </div>
        </div>
      ) : null}
    </section>
  )
}
