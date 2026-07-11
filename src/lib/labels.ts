export const modelLabel = (model: string): string => {
  const labels: Record<string, string> = {
    qwen3_8b: 'Qwen3 8B',
    qwen3_14b: 'Qwen3 14B',
    qwen3_32b: 'Qwen3 32B',
    llama_3_3_70b: 'Llama 3.3 70B',
    gemma_3_27b: 'Gemma 3 27B',
    mistral_small_3_2_24b: 'Mistral Small 3.2 24B',
  }
  return labels[model] ?? model
}

export const stageLabel = (stage: string): string => {
  const labels: Record<string, string> = {
    single_agent: 'Single Agent',
    context_agent_r1: 'Context Agent',
    option_agent_r1: 'Option Agent',
    sufficiency_agent_r1: 'Sufficiency Agent',
    judge_no_revision: 'Judge',
    context_agent_r2: 'Context Agent · With Revision',
    option_agent_r2: 'Option Agent · With Revision',
    sufficiency_agent_r2: 'Sufficiency Agent · With Revision',
    judge_with_revision: 'Judge · With Revision',
  }
  return labels[stage] ?? stage
}

export const variantLabel = (variant: string): string =>
  variant === 'disambiguated' ? 'Disambiguated' : 'Ambiguous'
