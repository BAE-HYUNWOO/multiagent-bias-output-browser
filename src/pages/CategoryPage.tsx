import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { EmptyView, ErrorView, LoadingView } from '../components/StatusView'
import { loadCategoryIndex, loadDatasetIndex, loadExperimentRootIndex } from '../lib/data'

export default function CategoryPage() {
  const { datasetId = '', categorySlug = '' } = useParams()
  const [searchParams] = useSearchParams()
  const experimentId = searchParams.get('experiment') ?? 'main'
  const run = searchParams.get('run')
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [empty, setEmpty] = useState(false)

  useEffect(() => {
    let cancelled = false
    setError(null)
    setEmpty(false)

    loadExperimentRootIndex(experimentId, run)
      .then((root) => {
        const datasetSummary = root.datasets.find((item) => item.id === datasetId)
        if (!datasetSummary) throw new Error(`Dataset not found: ${datasetId}`)
        return loadDatasetIndex(datasetSummary.path)
      })
      .then((dataset) => {
        const categorySummary = dataset.categories.find((item) => item.slug === categorySlug)
        if (!categorySummary) throw new Error(`Category not found: ${categorySlug}`)
        return loadCategoryIndex(categorySummary.path)
      })
      .then((category) => {
        if (cancelled) return
        const firstProblem = category.problems[0]
        if (!firstProblem) {
          setEmpty(true)
          return
        }

        navigate(
          `/dataset/${datasetId}/category/${categorySlug}/problem/${encodeURIComponent(firstProblem.key)}?${searchParams.toString()}`,
          { replace: true },
        )
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : String(reason))
        }
      })

    return () => {
      cancelled = true
    }
  }, [datasetId, categorySlug, experimentId, navigate, run, searchParams])

  if (error) return <ErrorView message={error} />
  if (empty) return <EmptyView />
  return <LoadingView message="Opening first problem..." />
}
