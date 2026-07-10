import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyView, ErrorView, LoadingView } from '../components/StatusView'
import { loadDatasetIndex, loadRootIndex } from '../lib/data'
import type { DatasetIndex, RootIndex } from '../types'

export default function HomePage() {
  const [index, setIndex] = useState<RootIndex | null>(null)
  const [openDatasetId, setOpenDatasetId] = useState<string | null>(null)
  const [datasetCache, setDatasetCache] = useState<Record<string, DatasetIndex>>({})
  const [loadingDatasetId, setLoadingDatasetId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRootIndex()
      .then(setIndex)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [])

  const toggleDataset = async (datasetId: string, datasetPath: string) => {
    if (openDatasetId === datasetId) {
      setOpenDatasetId(null)
      return
    }

    setOpenDatasetId(datasetId)
    setError(null)

    if (datasetCache[datasetId]) return

    setLoadingDatasetId(datasetId)
    try {
      const dataset = await loadDatasetIndex(datasetPath)
      setDatasetCache((current) => ({ ...current, [datasetId]: dataset }))
    } catch (reason: unknown) {
      setOpenDatasetId(null)
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoadingDatasetId(null)
    }
  }

  if (error) return <ErrorView message={error} />
  if (!index) return <LoadingView />
  if (!index.datasets.length) return <EmptyView />

  return (
    <div className="page-content home-page">
      <section className="dataset-folder-list" aria-label="Datasets">
        {index.datasets.map((dataset) => {
          const isOpen = openDatasetId === dataset.id
          const loadedDataset = datasetCache[dataset.id]
          const isLoading = loadingDatasetId === dataset.id

          return (
            <div className={`dataset-accordion-item${isOpen ? ' open' : ''}`} key={dataset.id}>
              <button
                className="dataset-folder-row"
                type="button"
                aria-expanded={isOpen}
                aria-controls={`dataset-categories-${dataset.id}`}
                onClick={() => void toggleDataset(dataset.id, dataset.path)}
              >
                <span className="dataset-folder-icon" aria-hidden="true">📁</span>
                <span className="folder-row-copy">
                  <strong>{dataset.label}</strong>
                  <small>{dataset.category_count} categories</small>
                </span>
                <span className="dataset-folder-arrow" aria-hidden="true">⌄</span>
              </button>

              <div
                className={`category-collapse${isOpen ? ' open' : ''}`}
                id={`dataset-categories-${dataset.id}`}
              >
                <div className="category-collapse-inner">
                  <div className="category-folder-list">
                    {isLoading ? (
                      <div className="category-loading-row">Loading categories...</div>
                    ) : null}

                    {loadedDataset?.categories.map((category) => (
                      <Link
                        className="category-folder-row"
                        key={category.slug}
                        to={`/dataset/${dataset.id}/category/${category.slug}`}
                      >
                        <span className="category-folder-icon" aria-hidden="true">📂</span>
                        <span className="folder-row-copy">
                          <strong>{category.name}</strong>
                          <small>{category.pair_count} problems</small>
                        </span>
                        <span className="category-folder-arrow" aria-hidden="true">›</span>
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </section>
    </div>
  )
}
