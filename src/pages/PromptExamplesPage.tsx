import { useEffect, useMemo, useState } from 'react'
import { ErrorView, LoadingView } from '../components/StatusView'
import { loadExperimentManifest, loadPromptExamples, withBase } from '../lib/data'
import { modelLabel } from '../lib/labels'
import type { ExperimentManifest, PromptExampleCard, PromptExampleEntry, PromptExamplesData } from '../types'

const GROUPS = [
  { id: 'single', label: 'Single Agent', description: 'The direct single-agent request used in the experiment.' },
  { id: 'multi_agent', label: 'Multi-Agent Flow', description: 'Round 1, judge, revision, and final-judge prompts from an actual completed multi-agent run.' },
  { id: 'neutral_agent', label: 'Neutral Agent Ablation', description: 'The Neutral Agent prompts replacing the Sufficiency Agent role.' },
] as const

function PromptCard({ card }: { card: PromptExampleCard }) {
  return <article className="prompt-example-card">
    <div className="prompt-card-header"><div><span className="prompt-stage-code">{card.stage}</span><h3>{card.label}</h3></div><span className="prompt-experiment-badge">{card.experiment}</span></div>
    <div className="prompt-section"><strong>System prompt</strong><pre>{card.system_prompt}</pre></div>
    <div className="prompt-section actual-prompt"><strong>Actually sent user prompt</strong><pre>{card.user_prompt}</pre></div>
    <div className="prompt-section prompt-output"><strong>Actual parsed output</strong><pre>{JSON.stringify(card.actual_output, null, 2)}</pre></div>
  </article>
}

export default function PromptExamplesPage() {
  const [data,setData] = useState<PromptExamplesData|null>(null)
  const [manifest,setManifest] = useState<ExperimentManifest|null>(null)
  const [languageCode,setLanguageCode] = useState('en')
  const [exampleIndex,setExampleIndex] = useState(0)
  const [menuOpen,setMenuOpen] = useState(false)
  const [error,setError] = useState<string|null>(null)

  useEffect(() => { Promise.all([loadPromptExamples(),loadExperimentManifest()]).then(([d,m]) => { setData(d); setManifest(m); setLanguageCode(d.languages[0]?.language_code ?? 'en') }).catch((e:unknown)=>setError(e instanceof Error?e.message:String(e))) }, [])
  const selectedLanguage = useMemo(()=>data?.languages.find(x=>x.language_code===languageCode)??null,[data,languageCode])
  const examples = useMemo<PromptExampleEntry[]>(()=>{
    if(!selectedLanguage) return []
    return selectedLanguage.examples?.length ? selectedLanguage.examples : [{model:selectedLanguage.model,model_id:selectedLanguage.model_id,item:selectedLanguage.item,cards:selectedLanguage.cards}]
  },[selectedLanguage])
  const active = examples[Math.min(exampleIndex,Math.max(examples.length-1,0))] ?? null
  if(error) return <ErrorView message={error}/>
  if(!data||!manifest||!selectedLanguage||!active) return <LoadingView/>
  const fields = [['Item',active.item.item_id],['Category',active.item.category],['Context type',active.item.context_type],['Model',modelLabel(active.model)]]

  return <div className="page-content prompt-examples-page">
    <section className="prompt-page-heading"><div><h1>Prompt Examples</h1><p>Actual system prompts, user prompts, and parsed outputs recorded from completed experiment runs.</p></div>{manifest.prompt_examples_download?<a className="secondary-button" href={withBase(manifest.prompt_examples_download)} download>Download Prompt Files</a>:null}</section>
    <section className="prompt-language-tabs" aria-label="Prompt language">{data.languages.map(l=><button type="button" key={l.language_code} className={l.language_code===languageCode?'active':''} onClick={()=>{setLanguageCode(l.language_code);setExampleIndex(0);setMenuOpen(false)}}><strong>{l.dataset}</strong><span>{l.language}</span></button>)}</section>
    <section className="prompt-example-selector-wrap">
      <div className="prompt-item-context prompt-item-context-selectable">{fields.map(([label,value])=><button key={label} type="button" className="prompt-context-selector" onClick={()=>setMenuOpen(v=>!v)}><span>{label}</span><strong>{value}</strong><small>Example {exampleIndex+1} / {examples.length} ▾</small></button>)}</div>
      {menuOpen?<div className="prompt-example-menu" role="listbox"><div className="prompt-example-menu-head"><span>Item</span><span>Category</span><span>Context type</span><span>Model</span></div>{examples.map((e,i)=><button type="button" role="option" aria-selected={i===exampleIndex} className={i===exampleIndex?'active':''} key={`${e.item.item_id}-${e.model}`} onClick={()=>{setExampleIndex(i);setMenuOpen(false)}}><span>{e.item.item_id}</span><span>{e.item.category}</span><span>{e.item.context_type}</span><span>{modelLabel(e.model)}</span></button>)}</div>:null}
    </section>
    {GROUPS.map(g=>{const cards=active.cards.filter(c=>c.group===g.id);if(!cards.length)return null;return <section className="prompt-group" key={g.id}><div className="prompt-group-heading"><h2>{g.label}</h2><p>{g.description}</p></div><div className="prompt-card-grid">{cards.map(c=><PromptCard key={`${c.group}-${c.stage}`} card={c}/>)}</div></section>})}
  </div>
}
