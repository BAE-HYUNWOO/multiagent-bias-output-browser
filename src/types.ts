export type ContextVariant = 'ambiguous' | 'disambiguated'

export type StageName =
  | 'single_agent'
  | 'context_agent_r1'
  | 'option_agent_r1'
  | 'sufficiency_agent_r1'
  | 'judge_no_revision'
  | 'context_agent_r2'
  | 'option_agent_r2'
  | 'sufficiency_agent_r2'
  | 'judge_with_revision'

export interface DatasetSummary {
  id: string
  label: string
  path: string
  category_count: number
  pair_count: number
  item_count: number
  models: string[]
}

export interface RootIndex {
  version: number
  generated_at: string | null
  experiment_id?: string
  experiment_label?: string
  run?: string | null
  available_runs?: string[]
  available_conditions?: ExperimentCondition[]
  datasets: DatasetSummary[]
  models: string[]
  totals: {
    categories: number
    pairs: number
    items: number
    stage_records: number
  }
}

export interface CategorySummary {
  name: string
  slug: string
  path: string
  pair_count: number
  item_count: number
  models: string[]
  download?: string | null
}

export interface DatasetIndex {
  dataset: string
  label: string
  category_count: number
  pair_count: number
  item_count: number
  models: string[]
  download?: string | null
  categories: CategorySummary[]
}

export interface VariantPreview {
  item_id: string
  preview: string
}

export interface PairSummary {
  key: string
  pair_id: string
  split: string
  title: string
  file: string
  variants: Partial<Record<ContextVariant, VariantPreview>>
  models: string[]
  has_condition_disagreement: boolean
}

export interface CategoryIndex {
  dataset: string
  category: string
  pair_count: number
  item_count: number
  models: string[]
  download?: string | null
  problems: PairSummary[]
}

export interface StageOutput {
  stage: StageName | string
  display_role?: string
  answer: string | null
  reason: string
  correct: boolean | null
  prompt_tokens?: number | null
  completion_tokens?: number | null
  total_cost_usd?: number | null
}

export interface ModelResult {
  single_agent: {
    final: StageOutput | null
  }
  multi_agent_no_revision: {
    stages: StageOutput[]
    final: StageOutput | null
  }
  multi_agent_with_revision: {
    stages: StageOutput[]
    final: StageOutput | null
  }
}

export interface ProblemVariant {
  item_id: string
  context_type: ContextVariant
  context: string
  question: string
  options: Record<string, string>
  correct_answer: string | null
  stereotype_answer: string | null
  anti_stereotype_answer: string | null
  unknown_answer: string | null
  results: Record<string, ModelResult>
}

export interface PairData {
  version: number
  key: string
  split: string
  dataset: string
  category: string
  pair_id: string
  variants: Partial<Record<ContextVariant, ProblemVariant>>
  models: string[]
}

export interface DownloadManifest {
  generated_at: string | null
  all_processed: string | null
  all_source_outputs?: string | null
  datasets: Record<
    string,
    {
      file: string | null
      categories: Record<string, string>
    }
  >
  experiments?: Record<string, string | null>
  prompt_examples?: string | null
}

export interface SiteConfig {
  title: string
  subtitle: string
  raw_release_url?: string
}

export type ExperimentCondition =
  | 'single_agent'
  | 'multi_agent_no_revision'
  | 'multi_agent_with_revision'

export interface ExperimentRun {
  id: string
  label: string
  path: string
}

export interface ExperimentSummary {
  id: string
  label: string
  description: string
  path: string | null
  summary_path: string | null
  available_conditions: ExperimentCondition[]
  runs: ExperimentRun[]
  default_run?: string
  download?: string | null
}

export interface ExperimentManifest {
  version: number
  generated_at: string | null
  experiments: ExperimentSummary[]
  prompt_examples_download?: string | null
  prompt_examples_path?: string | null
}

export interface ExperimentAnalysis {
  kind: 'neutral_agent_ablation' | 'sufficiency_repeatability'
  rows: Record<string, string | number | boolean>[]
  dataset_rows?: Record<string, string | number | boolean>[]
}

export interface PromptExampleCard {
  group: 'single' | 'multi_agent' | 'neutral_agent'
  label: string
  stage: string
  agent: string
  experiment: string
  system_prompt: string
  user_prompt: string
  actual_output: Record<string, unknown> | null
  order: number
}

export interface PromptExampleLanguage {
  language: string
  language_code: string
  dataset: string
  model: string
  model_id: string
  item: {
    item_id: string
    category: string
    context_type: string
    [key: string]: unknown
  }
  cards: PromptExampleCard[]
}

export interface PromptExamplesData {
  version: number
  generated_at: string | null
  model: string
  languages: PromptExampleLanguage[]
}
