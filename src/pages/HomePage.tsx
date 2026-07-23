import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ExperimentSummaryPanel from '../components/ExperimentSummaryPanel'
import { EmptyView, ErrorView, LoadingView } from '../components/StatusView'
import {
  loadDatasetIndex,
  loadExperimentAnalysis,
  loadExperimentManifest,
  loadExperimentRootIndex,
  withBase,
} from '../lib/data'
import type {
  DatasetIndex,
  ExperimentAnalysis,
  ExperimentManifest,
  RootIndex,
} from '../types'

export default function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [manifest, setManifest] = useState<ExperimentManifest | null>(null)
  const [index, setIndex] = useState<RootIndex | null>(null)
  const [analysis, setAnalysis] = useState<ExperimentAnalysis | null>(null)
  const [openDatasetId, setOpenDatasetId] = useState<string | null>(null)
  const [datasetCache, setDatasetCache] = useState<Record<string, DatasetIndex>>({})
  const [loadingDatasetId, setLoadingDatasetId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const experimentId = searchParams.get('experiment') ?? 'main'
  const requestedRun = searchParams.get('run')
  const experiment = useMemo(
    () => manifest?.experiments.find((item) => item.id === experimentId) ?? null,
    [experimentId, manifest],
  )
  const run =
    experiment?.runs.find((item) => item.id === requestedRun)?.id ??
    experiment?.default_run ??
    experiment?.runs[0]?.id ??
    null

  useEffect(() => {
    loadExperimentManifest()
      .then(setManifest)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [])

  useEffect(() => {
    if (!manifest) return
    const selected = manifest.experiments.find((item) => item.id === experimentId)
    if (!selected) {
      setSearchParams({ experiment: 'main' }, { replace: true })
      return
    }

    setIndex(null)
    setAnalysis(null)
    setDatasetCache({})
    setOpenDatasetId(null)
    setError(null)
    Promise.all([
      loadExperimentRootIndex(selected.id, run),
      loadExperimentAnalysis(selected),
    ])
      .then(([root, summary]) => {
        setIndex(root)
        setAnalysis(summary)
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [experimentId, manifest, run, setSearchParams])

  const setExperiment = (id: string) => {
    const next = new URLSearchParams()
    next.set('experiment', id)
    const selected = manifest?.experiments.find((item) => item.id === id)
    if (selected?.default_run) next.set('run', selected.default_run)
    setSearchParams(next)
  }

  const setRun = (value: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('run', value)
    setSearchParams(next)
  }

  const detailQuery = () => {
    const query = new URLSearchParams()
    query.set('experiment', experimentId)
    if (run) query.set('run', run)
    return query.toString()
  }

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
  if (!manifest || !experiment || !index) return <LoadingView />
  if (!index.datasets.length) return <EmptyView />

  return (
    <div className="page-content home-page">
      <section className="experiment-switcher" aria-label="Experiments">
        {manifest.experiments.map((item) => (
          <button
            type="button"
            key={item.id}
            className={`experiment-card${item.id === experimentId ? ' active' : ''}`}
            onClick={() => setExperiment(item.id)}
          >
            <strong>{item.label}</strong>
            <span>{item.description}</span>
          </button>
        ))}
      </section>

      <section className="experiment-toolbar">
        <div>
          <span className="eyebrow">Selected experiment</span>
          <h1>{experiment.label}</h1>
          <p>
            {index.totals.items.toLocaleString()} questions ·{' '}
            {index.models.length} models ·{' '}
            {index.totals.stage_records.toLocaleString()} stage outputs
          </p>
        </div>
        <div className="experiment-toolbar-actions">
          {experiment.runs.length ? (
            <label className="run-control">
              <span>Run</span>
              <select value={run ?? ''} onChange={(event) => setRun(event.target.value)}>
                {experiment.runs.map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
            </label>
          ) : null}
          {experiment.download ? (
            <a className="secondary-button" href={withBase(experiment.download)} download>
              Download
            </a>
          ) : null}
          {manifest.prompt_examples_download ? (
            <a
              className="secondary-button"
              href={withBase(manifest.prompt_examples_download)}
              download
            >
              Prompt Examples
            </a>
          ) : null}
        </div>
      </section>

      <ExperimentSummaryPanel analysis={analysis} />

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
                        to={`/dataset/${dataset.id}/category/${category.slug}?${detailQuery()}`}
                      >
                        <span className="category-folder-icon" aria-hidden="true">📂</span>
                        <span className="folder-row-copy">
                          <strong>{category.name}</strong>
                          <small>{category.pair_count} problems</small>
                        </span>
                        <span className="dataset-folder-arrow" aria-hidden="true">›</span>
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
