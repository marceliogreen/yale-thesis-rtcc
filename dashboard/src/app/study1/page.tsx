import clearanceData from '@/data/study1/clearance_rates.json';
import prePostData from '@/data/study1/pre_post_summary.json';
import verifiedDates from '@/data/study1/verified_dates.json';

export default function Study1Page() {
  const treatmentCities = ['Albuquerque', 'Chicago', 'Fresno', 'Miami', 'New Orleans', 'St. Louis'];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-serif font-bold text-yale mb-2">Study 1: RTCC Effectiveness</h1>
      <p className="text-muted mb-8 max-w-3xl">
        Multi-method evaluation of Real-Time Crime Center impact on homicide clearance rates across 8 treatment cities and 371 comparison agencies, using data from 2007 to 2024.
      </p>

      {/* Treatment Cities */}
      <section className="mb-12">
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Treatment Cities</h2>
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="text-left p-3 font-medium text-muted">City</th>
                  <th className="text-left p-3 font-medium text-muted">RTCC Year</th>
                  <th className="text-right p-3 font-medium text-muted">Pre Clearance</th>
                  <th className="text-right p-3 font-medium text-muted">Post Clearance</th>
                  <th className="text-right p-3 font-medium text-muted">Change</th>
                </tr>
              </thead>
              <tbody>
                {prePostData.map((row) => (
                  <tr key={row.city} className="border-b border-border hover:bg-gray-50">
                    <td className="p-3 font-medium text-dark">{row.city}</td>
                    <td className="p-3 text-muted">{row.rtcc_year}</td>
                    <td className="p-3 text-right">{typeof row.pre_clearance === 'number' ? `${row.pre_clearance.toFixed(1)}%` : 'N/A'}</td>
                    <td className="p-3 text-right">{typeof row.post_clearance === 'number' ? `${row.post_clearance.toFixed(1)}%` : 'N/A'}</td>
                    <td className="p-3 text-right font-medium">
                      {typeof row.change_pp === 'number' ? (
                        <span className={row.change_pp < 0 ? 'text-red' : 'text-green'}>{row.change_pp > 0 ? '+' : ''}{row.change_pp.toFixed(1)} pp</span>
                      ) : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Methodology Summary */}
      <section className="mb-12">
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Analytical Methods</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { name: 'Bayesian ITS', desc: 'Hierarchical partial-pooling interrupted time series with MCMC estimation' },
            { name: 'PSM-DiD', desc: 'Propensity-score matched difference-in-differences with nearest-neighbor matching' },
            { name: 'Monte Carlo', desc: '10,000-iteration parametric bootstrap with aggregate distribution parameters' },
            { name: 'Prophet', desc: 'Facebook Prophet counterfactual forecasting for treated cities' },
            { name: 'XGBoost + SHAP', desc: 'Gradient-boosted classifier with SHAP feature importance for causal attribution' },
            { name: 'Causal Forest', desc: 'EconML CausalForestDML for heterogeneous treatment effect estimation' },
          ].map(method => (
            <div key={method.name} className="bg-white rounded-lg border border-border p-5">
              <h3 className="font-serif font-bold text-dark mb-1">{method.name}</h3>
              <p className="text-xs text-muted leading-relaxed">{method.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Data Sources */}
      <section>
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Data Sources</h2>
        <div className="bg-white rounded-xl border border-border p-6">
          <ul className="text-sm text-muted space-y-2">
            <li><strong className="text-dark">UCR Return A</strong> (Kaplan, OpenICPSR 100707-V22) — annual homicide counts and clearances, 1960–2024</li>
            <li><strong className="text-dark">FBI CDE API</strong> — supplementary real-time data pulls for treatment cities</li>
            <li><strong className="text-dark">LEMAS 2020</strong> — law enforcement agency characteristics for covariate matching</li>
            <li><strong className="text-dark">ACS 5-Year</strong> — population estimates for comparison pool construction</li>
            <li><strong className="text-dark">RTCC verification</strong> — multi-source date verification (press releases, city documents, news archives)</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
