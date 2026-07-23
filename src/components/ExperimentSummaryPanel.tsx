import type { ExperimentAnalysis } from '../types'
import { modelLabel } from '../lib/labels'

const percent = (value: unknown) => {
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : '—'
}

const signedPoints = (value: unknown) => {
  const number = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(number)) return '—'
  const points = number * 100
  return `${points > 0 ? '+' : ''}${points.toFixed(1)} pp`
}

export default function ExperimentSummaryPanel({
  analysis,
}: {
  analysis: ExperimentAnalysis | null
}) {
  if (!analysis) return null

  if (analysis.kind === 'neutral_agent_ablation') {
    return (
      <section className="analysis-panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Paired comparison</span>
            <h2>Original vs Neutral Agent</h2>
          </div>
        </div>
        <div className="analysis-table-wrap">
          <table className="analysis-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Dataset</th>
                <th>Condition</th>
                <th>N</th>
                <th>Original</th>
                <th>Neutral</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {analysis.rows.map((row, index) => (
                <tr key={`${row.model}-${row.dataset}-${row.condition}-${index}`}>
                  <td>{modelLabel(String(row.model))}</td>
                  <td>{String(row.dataset)}</td>
                  <td>
                    {String(row.condition) === 'multi_agent_with_revision'
                      ? 'With Revision'
                      : 'Without Revision'}
                  </td>
                  <td>{Number(row.paired_n).toLocaleString()}</td>
                  <td>{percent(row.original_accuracy)}</td>
                  <td>{percent(row.neutral_accuracy)}</td>
                  <td>{signedPoints(row.accuracy_change)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    )
  }

  return (
    <section className="analysis-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Three-run stability</span>
          <h2>Repeatability Summary</h2>
        </div>
      </div>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Condition</th>
              <th>Items</th>
              <th>All Runs Same</th>
              <th>Changed</th>
              <th>Pairwise Agreement</th>
              <th>Mean Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {analysis.rows.map((row, index) => (
              <tr key={`${row.model}-${row.condition}-${index}`}>
                <td>{modelLabel(String(row.model))}</td>
                <td>
                  {String(row.condition) === 'multi_agent_with_revision'
                    ? 'With Revision'
                    : 'Without Revision'}
                </td>
                <td>{Number(row.n_item_models).toLocaleString()}</td>
                <td>{percent(row.all_runs_same_rate)}</td>
                <td>{percent(row.changed_across_runs_rate)}</td>
                <td>{percent(row.mean_pairwise_agreement)}</td>
                <td>{percent(row.mean_accuracy_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
