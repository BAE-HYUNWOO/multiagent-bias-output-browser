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

function stageForDisplay(stage: StageOutput | null, experimentId?: string): StageOutput | null {
  if (!stage || experimentId !== 'neutral_agent_ablation') return stage
  if (stage.stage === 'sufficiency_agent_r1') return { ...stage, display_role: 'neutral_agent_r1' }
  if (stage.stage === 'sufficiency_agent_r2') return { ...stage, display_role: 'neutral_agent_r2' }
  return stage
}

function RoundGrid({ stages, experimentId }: { stages: StageOutput[]; experimentId?: string }) {
  return (
    <div className="agent-grid three-columns">
      <AgentCard stage={stageForDisplay(stageByName(stages, 'context_agent_r1'), experimentId)} />
      <AgentCard stage={stageForDisplay(stageByName(stages, 'option_agent_r1'), experimentId)} />
      <AgentCard stage={stageForDisplay(stageByName(stages, 'sufficiency_agent_r1'), experimentId)} />
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
  availableConditions?: ConditionId[]
  experimentId?: string
}

export default function ConditionViewer({
  result,
  models,
  model,
  onModelChange,
  condition,
  onConditionChange,
  availableConditions = ['single', 'no_revision', 'with_revision'],
  experimentId,
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
        {CONDITIONS.filter((item) => availableConditions.includes(item.id)).map((item) => (
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
          <RoundGrid stages={result.multi_agent_no_revision.stages} experimentId={experimentId} />
          <div className="flow-arrow">↓</div>
          <div className="final-result-wrap">
            <AgentCard stage={result.multi_agent_no_revision.final} emphasis />
          </div>
        </div>
      ) : null}

      {condition === 'with_revision' ? (
        <div className="flow-stack">
          <div className="flow-label">Round 1</div>
          <RoundGrid stages={result.multi_agent_with_revision.stages} experimentId={experimentId} />
          <div className="flow-arrow">↓</div>
          <div className="flow-label">Round 2</div>
          <div className="agent-grid three-columns">
            {revisionPairs.map(([r1, r2]) => {
              const before = stageByName(result.multi_agent_with_revision.stages, r1)
              const after = stageByName(result.multi_agent_with_revision.stages, r2)
              return (
                <AgentCard
                  key={r2}
                  stage={stageForDisplay(after, experimentId)}
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
