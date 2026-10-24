import { useCallback, useEffect, useMemo, useState } from 'react'

const PAGES = [
  { path: '/overview', label: 'Overview', eyebrow: 'Grid intelligence', title: 'A clearer view of a changing New England grid.', description: 'Connect official regional context with a checked Massachusetts site simulation—without mixing forecasts, pipelines, policy targets, or operating results.' },
  { path: '/grid-data', label: 'Grid data', eyebrow: 'Official-source snapshot', title: 'Recent public facts, with their limits attached.', description: 'Every value keeps its publisher, reference period, units, evidence type, and caveat. Nothing on this page is a live feed.' },
  { path: '/clean-options', label: 'Clean options', eyebrow: 'Portfolio view', title: 'Solar is one option—not the whole system.', description: 'Explore generation, storage, demand flexibility, and efficiency separately, then inspect the existing checked site dispatch comparison.' },
  { path: '/ai-draft', label: 'AI draft', eyebrow: 'Human review required', title: 'A simulated AI report grounded in cited evidence.', description: 'The narrative is deterministically template-generated for this demo. Numeric values come from official context or the independently checked site report.' },
  { path: '/approvals', label: 'Approvals', eyebrow: 'Human in the loop', title: 'Four people stand between a draft and simulated approval.', description: 'Technical, provider, government-data, and management reviews occur in order. No click here can spend money or operate equipment.' },
  { path: '/sources', label: 'Sources', eyebrow: 'Evidence ledger', title: 'Inspect the provenance behind every public-data claim.', description: 'Official publisher links are citations to a pinned, manually curated snapshot—not live adapters or proof of government endorsement.' },
]

const TITLES = {
  existing: 'Existing operation',
  rule_based: 'Clean-generation-first rule',
  optimized: 'Optimized dispatch',
}

function quantity(value, fallback = 'N/A') {
  return value ? `${Number(value.value).toLocaleString(undefined, { maximumFractionDigits: 3 })} ${value.unit}` : fallback
}

function percent(value) {
  return value == null ? 'N/A' : `${(Number(value) * 100).toFixed(0)}%`
}

function Status({ children, tone = 'neutral' }) {
  return <span className={`status status-${tone}`}>{children}</span>
}

function MetricCard({ metric }) {
  return (
    <article className="metric-card">
      <div className="metric-topline"><span>{metric.kind.replaceAll('_', ' ')}</span><Status tone="pending">Review pending</Status></div>
      <strong>{metric.value} <small>{metric.unit}</small></strong>
      <h3>{metric.label}</h3>
      <p>{metric.period}</p>
      <p className="limitation">{metric.limitation}</p>
    </article>
  )
}

function AlternativeCard({ item, baselineCost }) {
  const { metrics } = item
  const cost = Number(metrics.operating_cost.amount.value)
  const savings = baselineCost - cost
  return (
    <article className={`alternative ${item.alternative === 'optimized' ? 'featured' : ''}`}>
      <div className="card-heading">
        <div>
          <span className="eyebrow">{item.alternative.replace('_', ' ')}</span>
          <h3>{TITLES[item.alternative]}</h3>
        </div>
        <Status tone="success">Checked</Status>
      </div>
      <div className="cost"><strong>${cost.toFixed(2)}</strong><span>sample operating cost</span></div>
      <dl className="metrics">
        <div><dt>Screening savings</dt><dd>{item.alternative === 'existing' ? 'Baseline' : `$${savings.toFixed(2)}`}</dd></div>
        <div><dt>Maximum site import</dt><dd>{quantity(metrics.peak_import)}</dd></div>
        <div><dt>Critical service</dt><dd>{percent(metrics.critical_service_fraction)}</dd></div>
        <div><dt>Critical unserved</dt><dd>{quantity(metrics.outage_service.critical_unserved_energy)}</dd></div>
        <div><dt>Critical interruption</dt><dd>{quantity(metrics.outage_service.interruption_duration)}</dd></div>
        <div><dt>Purchased emissions</dt><dd>{quantity(metrics.purchased_electricity_emissions.estimate)}</dd></div>
        <div><dt>Clean-energy share</dt><dd>{percent(metrics.clean_energy_share.share)}</dd></div>
      </dl>
      <div className="card-footer">
        <span>{item.solver.status === 'not_applicable' ? 'Deterministic schedule' : `Solver: ${item.solver.status}`}</span>
        <span>Independent check: {item.independent_checker.status}</span>
      </div>
    </article>
  )
}

function Overview({ report, simulation }) {
  const featured = ['regional-energy-growth', 'proposed-resource-queue', 'ma-storage-installed', 'ma-average-retail-price']
  const metrics = simulation.official_data.metrics.filter((metric) => featured.includes(metric.id))
  const optimized = report.alternatives.find((item) => item.alternative === 'optimized')
  return (
    <>
      <section className="metric-grid featured-metrics">{metrics.map((metric) => <MetricCard key={metric.id} metric={metric} />)}</section>
      <section className="story-grid">
        <article className="story-card accent-card"><span className="story-number">01</span><h2>Demand is changing</h2><p>ISO New England forecasts higher annual electricity use as transportation and buildings electrify. The forecast is context, not a measured future.</p></article>
        <article className="story-card"><span className="story-number">02</span><h2>Supply is diversifying</h2><p>Wind, solar, storage, hydro, nuclear, geothermal, efficiency, and flexible demand have distinct roles. Proposed capacity is not operating capacity.</p></article>
        <article className="story-card"><span className="story-number">03</span><h2>Decisions need checks</h2><p>The site model reports {quantity(optimized.metrics.peak_import)} maximum import and {percent(optimized.metrics.critical_service_fraction)} critical service, then requires human review before any simulated approval.</p></article>
      </section>
      <section className="wide-panel approval-preview">
        <div><p className="eyebrow">Review state</p><h2>{simulation.approval_flow.status.replaceAll('_', ' ')}</h2><p>{simulation.approval_flow.authorization_effect}</p></div>
        <div className="progress-block"><strong>{simulation.approval_flow.progress}</strong><span>simulated approvals complete</span><a className="text-link" href="/approvals">Open approval inbox →</a></div>
      </section>
      <section className="details-grid">
        <article className="panel"><p className="eyebrow">What this is</p><h2>A transparent screening result</h2><ul>{report.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article className="panel muted"><p className="eyebrow">What this is not</p><h2>Claims intentionally excluded</h2><ul>{report.exclusions.map((item) => <li key={item}>{item}</li>)}</ul></article>
      </section>
    </>
  )
}

function GridData({ simulation }) {
  return (
    <>
      <section className="notice"><b>Snapshot date: {simulation.official_data.retrieved_on}</b><span>{simulation.official_data.content_note}</span></section>
      <section className="metric-grid">{simulation.official_data.metrics.map((metric) => <MetricCard key={metric.id} metric={metric} />)}</section>
    </>
  )
}

function CleanOptions({ report, simulation }) {
  const baselineCost = Number(report.alternatives[0].metrics.operating_cost.amount.value)
  return (
    <>
      <section className="options-grid">
        {simulation.official_data.clean_options.map((option, index) => (
          <article className="option-card" key={option.id}>
            <div className="option-index">{String(index + 1).padStart(2, '0')}</div>
            <Status>{option.category.replaceAll('_', ' ')}</Status>
            <h2>{option.name}</h2>
            <p>{option.contribution}</p>
            <div className="evidence"><b>Evidence</b><span>{option.evidence}</span></div>
            <p className="limitation">{option.limitation}</p>
          </article>
        ))}
      </section>
      <section className="section-heading comparison-heading"><div><p className="eyebrow">Checked site sample</p><h2>Three dispatch alternatives</h2></div><p>The legacy sample has generic clean generation and storage. It does not calculate separate wind, hydro, nuclear, or geothermal site scenarios.</p></section>
      <section className="alternatives">{report.alternatives.map((item) => <AlternativeCard key={item.alternative} item={item} baselineCost={baselineCost} />)}</section>
    </>
  )
}

function AiDraft({ simulation }) {
  const { ai_draft: draft } = simulation
  const metricById = Object.fromEntries(simulation.official_data.metrics.map((metric) => [metric.id, metric]))
  return (
    <>
      <section className="notice warning"><b>{draft.label.replaceAll('_', ' ')}</b><span>{draft.generator.disclosure}</span></section>
      <section className="report-layout">
        <article className="report-paper">
          <div className="report-meta"><Status tone="pending">{draft.status.replaceAll('_', ' ')}</Status><code>{draft.fingerprint.slice(0, 16)}…</code></div>
          <h2>{draft.title}</h2><p className="report-summary">{draft.summary}</p>
          <h3>Evidence-backed findings</h3>
          <ol className="findings">
            {draft.findings.map((finding, index) => (
              <li key={finding.text}><span>{String(index + 1).padStart(2, '0')}</span><div><p>{finding.text}</p><small>{finding.evidence_ids.map((id) => metricById[id]?.label || 'Checked Fast Judge schedule').join(' · ')}</small></div></li>
            ))}
          </ol>
          <h3>Proposed simulated action</h3>
          <div className="proposal"><b>{draft.proposed_action.name}</b><p>{draft.proposed_action.financial_scope}</p><p>{draft.proposed_action.operational_scope}</p><strong>{draft.proposed_action.effect}</strong></div>
        </article>
        <aside className="review-rail"><p className="eyebrow">Before approval</p><h2>Required checks</h2><ul>{draft.limitations.map((item) => <li key={item}>{item}</li>)}</ul><a className="primary-link" href="/approvals">Begin human review →</a></aside>
      </section>
    </>
  )
}

function Approvals({ simulation, onApprove, onReset, busyRole }) {
  const flow = simulation.approval_flow
  return (
    <>
      <section className="notice danger"><b>Simulation only</b><span>No identity is verified. These acknowledgements have no legal, financial, regulatory, procurement, or operational effect.</span></section>
      <section className="approval-header"><div><p className="eyebrow">Ordered quorum</p><h2>{flow.progress} reviews completed</h2><p>{flow.storage}</p></div><button className="secondary-button" onClick={onReset} disabled={busyRole !== ''}>Reset simulation</button></section>
      <section className="approval-list">
        {flow.roles.map((role, index) => (
          <article className={`approval-card approval-${role.status}`} key={role.id}>
            <div className="approval-step">{role.status === 'approved' ? '✓' : index + 1}</div>
            <div className="approval-copy"><div className="approval-title"><h2>{role.label}</h2><Status tone={role.status === 'approved' ? 'success' : role.status === 'ready' ? 'pending' : 'neutral'}>{role.status}</Status></div><b>{role.actor}</b><p>{role.scope}</p></div>
            <button className="approve-button" disabled={role.status !== 'ready' || busyRole !== ''} onClick={() => onApprove(role.id)}>{busyRole === role.id ? 'Recording…' : role.status === 'approved' ? 'Recorded' : role.status === 'ready' ? 'Record simulated approval' : 'Waiting'}</button>
          </article>
        ))}
      </section>
      {flow.next_role === null && <section className="completion"><span>✓</span><div><h2>Simulated authorization complete</h2><p>The workflow is complete for demonstration only. No action was transmitted and no funds were committed.</p></div></section>}
    </>
  )
}

function Sources({ simulation }) {
  return (
    <>
      <section className="snapshot-strip"><div><span>Snapshot</span><b>{simulation.official_data.snapshot_id}</b></div><div><span>Review status</span><b>{simulation.official_data.review_status.replaceAll('_', ' ')}</b></div><div><span>SHA-256</span><code>{simulation.official_snapshot_fingerprint}</code></div></section>
      <section className="source-list">
        {simulation.official_data.sources.map((source) => (
          <article className="source-card" key={source.id}>
            <div><Status>{source.publisher_type}</Status><h2>{source.title}</h2><p>{source.publisher}</p></div>
            <dl><div><dt>Reference period</dt><dd>{source.reference_period}</dd></div><div><dt>Limitation</dt><dd>{source.limitation}</dd></div></dl>
            <a href={source.url} target="_blank" rel="noreferrer">Open official publisher ↗</a>
          </article>
        ))}
      </section>
    </>
  )
}

export default function App() {
  const path = window.location.pathname === '/' ? '/overview' : window.location.pathname
  const page = PAGES.find((item) => item.path === path) || PAGES[0]
  const [report, setReport] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyRole, setBusyRole] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [reportResponse, simulationResponse] = await Promise.all([
        fetch('/api/sample-report', { headers: { Accept: 'application/json' } }),
        fetch('/api/simulation', { headers: { Accept: 'application/json' } }),
      ])
      if (!reportResponse.ok || !simulationResponse.ok) throw new Error('The full-stack demo is not ready')
      setReport(await reportResponse.json()); setSimulation(await simulationResponse.json())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load the demo')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { document.title = `${page.label} | OmniGridX` }, [page.label])

  const approve = async (role) => {
    setBusyRole(role); setError('')
    try {
      const response = await fetch('/api/simulation/approvals', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ role }) })
      const document = await response.json()
      if (!response.ok) throw new Error(document.error || 'Approval was not recorded')
      setSimulation(document)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Approval was not recorded') }
    finally { setBusyRole('') }
  }

  const reset = async () => {
    setBusyRole('reset'); setError('')
    try {
      const response = await fetch('/api/simulation/reset', { method: 'POST', headers: { Accept: 'application/json' } })
      if (!response.ok) throw new Error('Simulation was not reset')
      setSimulation(await response.json())
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Simulation was not reset') }
    finally { setBusyRole('') }
  }

  const content = useMemo(() => {
    if (!report || !simulation) return null
    if (page.path === '/grid-data') return <GridData simulation={simulation} />
    if (page.path === '/clean-options') return <CleanOptions report={report} simulation={simulation} />
    if (page.path === '/ai-draft') return <AiDraft simulation={simulation} />
    if (page.path === '/approvals') return <Approvals simulation={simulation} onApprove={approve} onReset={reset} busyRole={busyRole} />
    if (page.path === '/sources') return <Sources simulation={simulation} />
    return <Overview report={report} simulation={simulation} />
  }, [busyRole, page.path, report, simulation])

  if (loading && !report) return <main className="center" aria-live="polite"><div className="spinner" /><p>Loading checked reports and source evidence…</p></main>
  if (error && !report) return <main className="center"><p className="error" role="alert">{error}</p><button onClick={load}>Try again</button></main>

  return (
    <div className="app-shell">
      <a className="skip-link" href="#content">Skip to content</a>
      <header className="site-header">
        <div className="topbar"><a className="brand" href="/overview">OmniGrid<span>X</span></a><div className="demo-badge">Simulated full-stack demo</div></div>
        <nav className="page-nav" aria-label="Primary navigation">{PAGES.map((item) => <a key={item.path} href={item.path} aria-current={page.path === item.path ? 'page' : undefined}>{item.label}</a>)}</nav>
      </header>
      <section className="page-hero"><div><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p className="lede">{page.description}</p></div>{simulation && <div className="hero-status"><span>Workflow</span><b>{simulation.approval_flow.progress}</b><small>{simulation.approval_flow.status.replaceAll('_', ' ')}</small></div>}</section>
      <main id="content">{error && <p className="inline-error" role="alert">{error}</p>}{content}</main>
      <footer><span>OmniGridX · Massachusetts & New England</span><span>Simulation only · No login · No uploads · No real approvals or control</span></footer>
    </div>
  )
}
