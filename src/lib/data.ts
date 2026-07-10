import type {
  CategoryIndex,
  DatasetIndex,
  DownloadManifest,
  PairData,
  RootIndex,
  SiteConfig,
} from '../types'

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' })
  if (!response.ok) {
    throw new Error(`데이터를 불러오지 못했습니다: ${path} (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const loadRootIndex = () => fetchJson<RootIndex>('/data/index.json')
export const loadSiteConfig = () => fetchJson<SiteConfig>('/data/site_config.json')
export const loadDatasetIndex = (path: string) => fetchJson<DatasetIndex>(path)
export const loadCategoryIndex = (path: string) => fetchJson<CategoryIndex>(path)
export const loadPairData = (path: string) => fetchJson<PairData>(path)
export const loadDownloadManifest = () => fetchJson<DownloadManifest>('/downloads/manifest.json')
