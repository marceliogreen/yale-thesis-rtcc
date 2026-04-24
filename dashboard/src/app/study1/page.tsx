import prePostData from '@/data/study1/pre_post_summary.json';

const TREATMENT_CITIES = [
  { city: 'Hartford', state: 'CT', rtcc_year: 2015, population: 47068, note: 'Verified 2015 operational' },
  { city: 'Miami', state: 'FL', rtcc_year: 2016, population: 442241, note: 'Major RTCC hub' },
  { city: 'St. Louis', state: 'MO', rtcc_year: 2015, population: 293471, note: 'RTCC operational pre-2015' },
  { city: 'Newark', state: 'NJ', rtcc_year: 2018, population: 277140, note: 'NJ ROIC integration' },
  { city: 'New Orleans', state: 'LA', rtcc_year: 2017, population: 390144, note: 'Real-time monitoring center' },
  { city: 'Albuquerque', state: 'NM', rtcc_year: 2020, population: 564559, note: 'Verified 2020 adoption' },
  { city: 'Fresno', state: 'CA', rtcc_year: 2018, population: 542012, note: 'Fusion center integration' },
  { city: 'Chicago', state: 'IL', rtcc_year: 2017, population: 2693976, note: 'Strategic Decision Support Center' },
];

export default function Study1Page() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-2xl font-semibold text-yale mb-2">Study 1: RTCC Effectiveness</h1>
      <p className="text-sm text-muted mb-8 max-w-3xl">
        Multi-method evaluation of Real-Time Crime Center impact on homicide clearance rates across 8 treatment cities and 371 comparison agencies, using data from 2007 to 2024.
      </p>

      {/* Treatment Cities */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Treatment Cities</h2>
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="text-left p-3 font-medium text-muted">City</th>
                  <th className="text-left p-3 font-medium text-muted">State</th>
                  <th className="text-right p-3 font-medium text-muted">RTCC Year</th>
                  <th className="text-right p-3 font-medium text-muted">Population</th>
                </tr>
              </thead>
              <tbody>
                {TREATMENT_CITIES.map((row) => (
                  <tr key={row.city} className="border-b border-border hover:bg-gray-50">
                    <td className="p-3 font-medium text-dark">{row.city}</td>
                    <td className="p-3 text-muted">{row.state}</td>
                    <td className="p-3 text-right text-muted">{row.rtcc_year}</td>
                    <td className="p-3 text-right text-muted">{row.population.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Pre/Post Clearance Summary */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Pre/Post Clearance Rates</h2>
        <p className="text-xs text-muted mb-3">Cities with available clearance data from the analysis sample (2010-2017).</p>
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="text-left p-3 font-medium text-muted">City</th>
                  <th className="text-right p-3 font-medium text-muted">RTCC Year</th>
                  <th className="text-right p-3 font-medium text-muted">Pre Clearance</th>
                  <th className="text-right p-3 font-medium text-muted">Post Clearance</th>
                  <th className="text-right p-3 font-medium text-muted">Change</th>
                </tr>
              </thead>
              <tbody>
                {prePostData.map((row) => (
                  <tr key={row.city} className="border-b border-border hover:bg-gray-50">
                    <td className="p-3 font-medium text-dark">{row.city}</td>
                    <td className="p-3 text-right text-muted">{row.rtcc_year}</td>
                    <td className="p-3 text-right">{typeof row.pre_clearance === 'number' ? `${(row.pre_clearance * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td className="p-3 text-right">{typeof row.post_clearance === 'number' ? `${(row.post_clearance * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td className="p-3 text-right font-medium">
                      {typeof row.change_pp === 'number' ? (
                        <span className={row.change_pp < 0 ? 'text-red' : 'text-green'}>
                          {row.change_pp > 0 ? '+' : ''}{row.change_pp.toFixed(1)} pp
                        </span>
                      ) : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Methods */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Analytical Methods</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { name: 'Bayesian ITS', desc: 'Hierarchical partial-pooling interrupted time series with MCMC (4 chains, 2000 draws)' },
            { name: 'PSM-DiD', desc: 'Propensity-score matched difference-in-differences — primary causal estimate' },
            { name: 'Monte Carlo', desc: '10,000-iteration parametric bootstrap with aggregate distribution parameters' },
            { name: 'Prophet', desc: 'Facebook Prophet counterfactual forecasting for treated cities' },
            { name: 'XGBoost + SHAP', desc: 'Gradient-boosted classifier with SHAP feature importance' },
            { name: 'Causal Forest', desc: 'EconML CausalForestDML for heterogeneous treatment effects' },
          ].map(method => (
            <div key={method.name} className="bg-white rounded-lg border border-border p-4">
              <h3 className="font-semibold text-dark text-sm mb-1">{method.name}</h3>
              <p className="text-xs text-muted leading-snug">{method.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Data Sources */}
      <section>
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Data Sources</h2>
        <div className="bg-white rounded-lg border border-border p-5">
          <ul className="text-sm text-muted space-y-2">
            <li><strong className="text-dark">UCR Return A</strong> (Kaplan, ICPSR 100707-V22) — annual homicide counts and clearances</li>
            <li><strong className="text-dark">FBI CDE API</strong> — supplementary real-time data for treatment cities</li>
            <li><strong className="text-dark">LEMAS 2020</strong> — law enforcement agency characteristics for covariate matching</li>
            <li><strong className="text-dark">ACS 5-Year</strong> — population estimates for comparison pool construction</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
