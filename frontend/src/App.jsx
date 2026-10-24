import { useCallback, useEffect, useState } from 'react'

const TITLES = {
  existing: 'Existing operation',
  rule_based: 'Solar-first rule',
  optimized: 'Optimized dispatch',
}

function quantity(value, fallback = 'N/A') {
  return value ? `${Number(value.value).toLocaleString(undefined, { maximumFractionDigits: 3 })} ${value.unit}` : fallback
}

function percent(value) {
  return value == null ? 'N/A' : `${(Number(value) * 100).toFixed(0)}%`
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
          <h2>{TITLES[item.alternative]}</h2>
        </div>
        <span className="status">Checked</span>
      </div>
      <div className="cost">
        <strong>${cost.toFixed(2)}</strong>
        <span>sample operating cost</span>
      </div>
      <dl className="metrics">
        <div><dt>Screening savings</dt><dd>{item.alternative === 'existing' ? 'Baseline' : `$${savings.toFixed(2)}`}</dd></div>
        <div><dt>Peak import</dt><dd>{quantity(metrics.peak_import)}</dd></div>
        <div><dt>Critical service</dt><dd>{percent(metrics.critical_service_fraction)}</dd></div>
        <div><dt>Critical unserved</dt><dd>{quantity(metrics.outage_service.critical_unserved_energy)}</dd></div>
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

export default function App() {
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (rerun = false) => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(rerun ? '/api/sample-run' : '/api/sample-report', {
        method: rerun ? 'POST' : 'GET',
        headers: { Accept: 'application/json' },
      })
      if (!response.ok) throw new Error(`Request failed (${response.status})`)
      setReport(await response.json())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load the sample report')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading && !report) return <main className="center" aria-live="polite"><div className="spinner" /><p>Running the bundled sample…</p></main>
  if (error && !report) return <main className="center"><p className="error">{error}</p><button onClick={() => load()}>Try again</button></main>

  const baselineCost = Number(report.alternatives[0].metrics.operating_cost.amount.value)
  return (
    <div className="app-shell">
      <header className="hero">
        <nav><a className="brand" href="/">OmniGrid<span>X</span></a><span className="demo-badge">Sample-only demo</span></nav>
        <div className="hero-copy">
          <div>
            <p className="eyebrow">Massachusetts commercial-site screening</p>
            <h1>See how one site could use energy differently.</h1>
            <p className="lede">Three schedules. One frozen sample. Transparent cost, resilience, emissions, and clean-energy outcomes.</p>
          </div>
          <button className="run-button" disabled={loading} onClick={() => load(true)}>{loading ? 'Running…' : 'Run sample again'} <span aria-hidden="true">→</span></button>
        </div>
        <div className="run-meta">
          <span><b>Sample</b> {report.sample_id}</span>
          <span><b>Manifest</b> {report.manifest.fingerprint.slice(0, 12)}…</span>
          <span><b>Report</b> {report.report_fingerprint.slice(0, 12)}…</span>
        </div>
      </header>

      <main>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <section className="section-heading">
          <div><p className="eyebrow">Checked comparison</p><h2>Dispatch alternatives</h2></div>
          <p>All schedules use identical inputs and pass an independent constraint checker.</p>
        </section>
        <section className="alternatives">
          {report.alternatives.map((item) => <AlternativeCard key={item.alternative} item={item} baselineCost={baselineCost} />)}
        </section>

        <section className="details-grid">
          <article className="panel">
            <p className="eyebrow">What this is</p>
            <h2>A transparent screening result</h2>
            <ul>{report.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
          <article className="panel muted">
            <p className="eyebrow">What this is not</p>
            <h2>Claims intentionally excluded</h2>
            <ul>{report.exclusions.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
        </section>

        <section className="disclosure">
          <div><p className="eyebrow">Read before using</p><h2>Screening disclosures</h2></div>
          <ol>{report.disclosures.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, '0')}</span>{item}</li>)}</ol>
        </section>
      </main>
      <footer><span>OmniGridX Fast Judge MVP</span><span>No login · No uploads · No customer data</span></footer>
    </div>
  )
}
