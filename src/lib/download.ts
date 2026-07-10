import type { PairData, ProblemVariant } from '../types'

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function downloadJson(value: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  saveBlob(blob, filename)
}

function csvCell(value: unknown): string {
  const text = value == null ? '' : String(value)
  return `"${text.replaceAll('"', '""')}"`
}

export function downloadVariantCsv(
  pair: PairData,
  variant: ProblemVariant,
  model: string,
): void {
  const modelResult = variant.results[model]
  const rows: unknown[][] = [
    [
      'split',
      'dataset',
      'category',
      'pair_id',
      'item_id',
      'context_type',
      'model',
      'condition',
      'stage',
      'answer',
      'correct',
      'reason',
    ],
  ]

  const pushStage = (condition: string, stage: typeof modelResult.single_agent.final) => {
    if (!stage) return
    rows.push([
      pair.split,
      pair.dataset,
      pair.category,
      pair.pair_id,
      variant.item_id,
      variant.context_type,
      model,
      condition,
      stage.stage,
      stage.answer,
      stage.correct,
      stage.reason,
    ])
  }

  pushStage('single_agent', modelResult.single_agent.final)
  modelResult.multi_agent_no_revision.stages.forEach((stage) =>
    pushStage('multi_agent_no_revision', stage),
  )
  modelResult.multi_agent_with_revision.stages.forEach((stage) =>
    pushStage('multi_agent_with_revision', stage),
  )

  const csv = rows.map((row) => row.map(csvCell).join(',')).join('\r\n')
  saveBlob(
    new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }),
    `${pair.dataset}_${pair.category}_${pair.pair_id}_${variant.context_type}_${model}.csv`,
  )
}
