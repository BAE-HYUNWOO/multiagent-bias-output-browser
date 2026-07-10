import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Breadcrumbs from '../components/Breadcrumbs'
import { ErrorView, LoadingView } from '../components/StatusView'
import { loadDatasetIndex, loadRootIndex } from '../lib/data'
import type { DatasetIndex } from '../types'

export default function DatasetPage() {
  const { datasetId = '' } = useParams()
  const [dataset, setDataset] = useState<DatasetIndex | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDataset(null)
    setError(null)
    loadRootIndex()
      .then((root) => {
        const summary = root.datasets.find((item) => item.id === datasetId)
        if (!summary) throw new Error(`Dataset을 찾을 수 없습니다: ${datasetId}`)
        return loadDatasetIndex(summary.path)
      })
      .then(setDataset)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [datasetId])

  if (error) return <ErrorView message={error} />
  if (!dataset) return <LoadingView />

  return (
    <div className="page-content">
      <Breadcrumbs items={[{ label: 'Datasets', to: '/' }, { label: dataset.label }]} />
      <section className="page-title-row">
        <div>
          <span className="eyebrow">Dataset folder</span>
          <h1>{dataset.label}</h1>
          <p>
            {dataset.category_count} categories · {dataset.pair_count.toLocaleString()} matched pairs ·{' '}
            {dataset.models.length} models
          </p>
        </div>
        {dataset.download ? (
          <a className="secondary-button" href={dataset.download} download>
            Download {dataset.label}
          </a>
        ) : null}
      </section>

      <section className="category-grid">
        {dataset.categories.map((category) => (
          <Link
            className="category-card"
            key={category.slug}
            to={`/dataset/${datasetId}/category/${category.slug}`}
          >
            <span className="category-folder">📂</span>
            <div>
              <h2>{category.name}</h2>
              <p>{category.pair_count} pairs · {category.item_count} questions</p>
            </div>
            <span className="card-arrow">→</span>
          </Link>
        ))}
      </section>
    </div>
  )
}
