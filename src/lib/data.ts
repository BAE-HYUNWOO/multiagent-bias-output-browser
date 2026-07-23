import type {
  CategoryIndex,
  DatasetIndex,
  DownloadManifest,
  ExperimentAnalysis,
  ExperimentManifest,
  ExperimentSummary,
  PairData,
  PromptExamplesData,
  RootIndex,
  SiteConfig,
} from '../types'

export function withBase(path: string): string {
  if (
    path.startsWith('http://') ||
    path.startsWith('https://') ||
    path.startsWith('data:') ||
    path.startsWith('blob:')
  ) {
    return path
  }

  const cleanPath = path.replace(/^\.?\//, '')
  return `${import.meta.env.BASE_URL}${cleanPath}`
}

async function fetchJson<T>(path: string): Promise<T> {
  const resolvedPath = withBase(path)
  const response = await fetch(resolvedPath, { cache: 'no-store' })
  if (!response.ok) {
    throw new Error(`데이터를 불러오지 못했습니다: ${resolvedPath} (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const loadRootIndex = () => fetchJson<RootIndex>('/data/index.json')
export const loadExperimentManifest = () =>
  fetchJson<ExperimentManifest>('/data/experiments.json')
export const loadExperimentRootIndex = async (
  experimentId: string,
  run?: string | null,
): Promise<RootIndex> => {
  const manifest = await loadExperimentManifest()
  const experiment = manifest.experiments.find((item) => item.id === experimentId)
  if (!experiment) throw new Error(`Experiment not found: ${experimentId}`)

  if (experiment.runs.length) {
    const selectedRun =
      experiment.runs.find((item) => item.id === run) ??
      experiment.runs.find((item) => item.id === experiment.default_run) ??
      experiment.runs[0]
    if (!selectedRun) throw new Error(`No run data found: ${experimentId}`)
    return fetchJson<RootIndex>(selectedRun.path)
  }

  if (!experiment.path) throw new Error(`Experiment data path is missing: ${experimentId}`)
  return fetchJson<RootIndex>(experiment.path)
}
export const loadExperimentAnalysis = (experiment: ExperimentSummary) =>
  experiment.summary_path
    ? fetchJson<ExperimentAnalysis>(experiment.summary_path)
    : Promise.resolve(null)
export const loadSiteConfig = () => fetchJson<SiteConfig>('/data/site_config.json')
export const loadDatasetIndex = (path: string) => fetchJson<DatasetIndex>(path)
export const loadCategoryIndex = (path: string) => fetchJson<CategoryIndex>(path)
export const loadPairData = (path: string) => fetchJson<PairData>(path)
export const loadPromptExamples = () =>
  fetchJson<PromptExamplesData>('/data/prompt_examples.json')
export const loadDownloadManifest = () => fetchJson<DownloadManifest>('/downloads/manifest.json')
