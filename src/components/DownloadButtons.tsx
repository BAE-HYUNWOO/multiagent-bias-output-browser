import type { PairData, ProblemVariant } from '../types'
import { downloadJson, downloadVariantCsv } from '../lib/download'

export default function DownloadButtons({
  pair,
  variant,
  model,
}: {
  pair: PairData
  variant: ProblemVariant
  model: string
}) {
  const selected = {
    split: pair.split,
    dataset: pair.dataset,
    category: pair.category,
    pair_id: pair.pair_id,
    variant,
    model,
    result: variant.results[model],
  }

  const base = `${pair.dataset}_${pair.category}_${pair.pair_id}_${variant.context_type}_${model}`

  return (
    <div className="download-button-row">
      <button type="button" onClick={() => downloadJson(selected, `${base}.json`)}>
        Download JSON
      </button>
      <button type="button" onClick={() => downloadVariantCsv(pair, variant, model)}>
        Download CSV
      </button>
    </div>
  )
}
