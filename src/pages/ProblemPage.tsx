import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import ConditionViewer, { type ConditionId } from '../components/ConditionViewer'
import QuestionPanel from '../components/QuestionPanel'
import { ErrorView, LoadingView } from '../components/StatusView'
import { loadCategoryIndex, loadDatasetIndex, loadPairData, loadRootIndex } from '../lib/data'
import type { CategoryIndex, ContextVariant, PairData, PairSummary } from '../types'

export default function ProblemPage() {
  const { datasetId = '', categorySlug = '', pairKey = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [category, setCategory] = useState<CategoryIndex | null>(null)
  const [pair, setPair] = useState<PairData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [problemMenuOpen, setProblemMenuOpen] = useState(false)
  const problemPickerRef = useRef<HTMLDivElement>(null)

  const decodedPairKey = useMemo(() => {
    try {
      return decodeURIComponent(pairKey)
    } catch {
      return pairKey
    }
  }, [pairKey])

  useEffect(() => {
    setCategory(null)
    setPair(null)
    setError(null)

    loadRootIndex()
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
      .then((loadedCategory) => {
        setCategory(loadedCategory)
        const summary = loadedCategory.problems.find((item) => item.key === decodedPairKey)
        if (!summary) throw new Error('Problem not found.')
        return loadPairData(summary.file)
      })
      .then(setPair)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [datasetId, categorySlug, decodedPairKey])

  useEffect(() => {
    if (!problemMenuOpen) return

    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!problemPickerRef.current?.contains(event.target as Node)) {
        setProblemMenuOpen(false)
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setProblemMenuOpen(false)
    }

    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [problemMenuOpen])

  if (error) return <ErrorView message={error} />
  if (!category || !pair) return <LoadingView message="Loading problem results..." />

  const availableVariants = Object.keys(pair.variants).filter(
    (variant) => Boolean(pair.variants[variant as ContextVariant]),
  ) as ContextVariant[]

  const requestedVariant = searchParams.get('variant') as ContextVariant | null
  const selectedVariant =
    (requestedVariant && pair.variants[requestedVariant] ? requestedVariant : availableVariants[0]) ??
    'ambiguous'
  const activeVariant = pair.variants[selectedVariant]

  if (!activeVariant) return <LoadingView message="Loading problem results..." />

  const requestedModel = searchParams.get('model')
  const model =
    (requestedModel && activeVariant.results[requestedModel] ? requestedModel : pair.models[0]) ?? ''
  const modelResult = activeVariant.results[model]

  const requestedCondition = searchParams.get('condition') as ConditionId | null
  const condition: ConditionId =
    requestedCondition === 'no_revision' || requestedCondition === 'with_revision'
      ? requestedCondition
      : 'single'

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams)
    next.set(key, value)
    setSearchParams(next)
  }

  const changeProblem = (nextPairKey: string) => {
    setProblemMenuOpen(false)
    const query = searchParams.toString()
    navigate(
      `/dataset/${datasetId}/category/${categorySlug}/problem/${encodeURIComponent(nextPairKey)}${query ? `?${query}` : ''}`,
    )
  }

  const getProblemDisplay = (problem: PairSummary) => {
    const questionId =
      problem.variants[selectedVariant]?.item_id ||
      problem.variants.ambiguous?.item_id ||
      problem.variants.disambiguated?.item_id ||
      problem.pair_id ||
      problem.key

    const questionText =
      problem.variants[selectedVariant]?.preview ||
      problem.variants.ambiguous?.preview ||
      problem.variants.disambiguated?.preview ||
      problem.title ||
      problem.key

    return { questionId, questionText }
  }

  const selectedProblem = category.problems.find((problem) => problem.key === decodedPairKey)
  const selectedProblemDisplay = selectedProblem
    ? getProblemDisplay(selectedProblem)
    : { questionId: decodedPairKey, questionText: '' }

  return (
    <div className="page-content problem-detail-page">
      <section className="problem-picker-bar" aria-label="Problem selector">
        <label id="problem-picker-label">Problem</label>
        <div
          className={`problem-picker-dropdown${problemMenuOpen ? ' open' : ''}`}
          ref={problemPickerRef}
        >
          <button
            type="button"
            className="problem-picker-trigger"
            aria-labelledby="problem-picker-label"
            aria-haspopup="listbox"
            aria-expanded={problemMenuOpen}
            onClick={() => setProblemMenuOpen((open) => !open)}
          >
            <span className="problem-picker-value">
              <strong>{selectedProblemDisplay.questionId}</strong>
              <span> : {selectedProblemDisplay.questionText}</span>
            </span>
            <span className="problem-picker-chevron" aria-hidden="true">⌄</span>
          </button>

          {problemMenuOpen ? (
            <div className="problem-picker-menu" role="listbox" aria-label="Problems">
              {category.problems.map((problem) => {
                const { questionId, questionText } = getProblemDisplay(problem)
                const active = problem.key === decodedPairKey
                return (
                  <button
                    type="button"
                    role="option"
                    aria-selected={active}
                    className={active ? 'active' : ''}
                    key={problem.key}
                    onClick={() => changeProblem(problem.key)}
                  >
                    <strong>{questionId}</strong>
                    <span> : {questionText}</span>
                  </button>
                )
              })}
            </div>
          ) : null}
        </div>
      </section>

      {!modelResult ? (
        <LoadingView message="Loading model results..." />
      ) : (
        <section className="problem-detail-grid">
          <QuestionPanel
            variant={activeVariant}
            availableVariants={availableVariants}
            selectedVariant={selectedVariant}
            onVariantChange={(value) => updateParam('variant', value)}
          />
          <ConditionViewer
            result={modelResult}
            models={pair.models}
            model={model}
            onModelChange={(value) => updateParam('model', value)}
            condition={condition}
            onConditionChange={(value) => updateParam('condition', value)}
          />
        </section>
      )}
    </div>
  )
}
