import type {
  CategoryIndex,
  DatasetIndex,
  DownloadManifest,
  PairData,
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
export const loadSiteConfig = () => fetchJson<SiteConfig>('/data/site_config.json')
export const loadDatasetIndex = (path: string) => fetchJson<DatasetIndex>(path)
export const loadCategoryIndex = (path: string) => fetchJson<CategoryIndex>(path)
export const loadPairData = (path: string) => fetchJson<PairData>(path)
export const loadDownloadManifest = () => fetchJson<DownloadManifest>('/downloads/manifest.json')
