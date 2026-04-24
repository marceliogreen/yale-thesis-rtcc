import DfrComparisonChart from '@/components/charts/DfrComparisonChart';
import cogSciData from '@/data/study2/cog_sci_comparison.json';
import dfrData from '@/data/study2/dfr_cross_program.json';
import benchmarkData from '@/data/study2/benchmark_mapping.json';

export default function Study2Page() {
  const supported = benchmarkData.filter(b => b.status === 'supported').length;
  const total = benchmarkData.length;

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-2xl font-semibold text-yale mb-2">Study 2: Drone-as-First-Responder Programs</h1>
      <p className="text-sm text-muted mb-8 max-w-3xl">
        Drone programs in three cities evaluated through a cognitive science lens — does the technology actually help operators perceive, understand, and decide better?
      </p>

      {/* At a Glance */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">At a Glance</h2>
        <div className="grid sm:grid-cols-3 gap-3 mb-6">
          <div className="bg-white rounded-lg border-l-4 border-yale p-4 border border-border">
            <div className="text-xs text-muted uppercase tracking-wide">Programs Studied</div>
            <div className="text-2xl font-bold text-dark mt-1">3</div>
            <div className="text-xs text-muted mt-1">Chula Vista CA, Elizabeth NJ, Cincinnati OH</div>
          </div>
          <div className="bg-white rounded-lg border-l-4 border-green p-4 border border-border">
            <div className="text-xs text-muted uppercase tracking-wide">Predictions Confirmed</div>
            <div className="text-2xl font-bold text-dark mt-1">{supported} / {total}</div>
            <div className="text-xs text-muted mt-1">Cognitive science predictions supported by operational data</div>
          </div>
          <div className="bg-white rounded-lg border-l-4 border-orange p-4 border border-border">
            <div className="text-xs text-muted uppercase tracking-wide">Fastest Response</div>
            <div className="text-2xl font-bold text-dark mt-1">94s</div>
            <div className="text-xs text-muted mt-1">Elizabeth NJ — but 31% success rate reveals speed-accuracy tradeoff</div>
          </div>
        </div>
      </section>

      {/* What This Means */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">What This Means</h2>
        <div className="bg-white rounded-lg border border-border p-6 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-dark mb-1">Drones arrive fast — but speed does not equal understanding</h3>
            <p className="text-sm text-muted leading-relaxed">Elizabeth NJ drones arrive in 94 seconds (2.5x faster than Chula Vista), yet their mission success rate is only 31%. This directly confirms Endsley&apos;s theory: detecting a situation quickly (Level 1) does not mean understanding it correctly (Level 2). The technology improves response time but not necessarily decision quality.</p>
          </div>
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-semibold text-dark mb-1">Operators face cognitive overload across all three programs</h3>
            <p className="text-sm text-muted leading-relaxed">8% of Cincinnati flights exceed the 20-minute vigilance threshold where attention degrades. Elizabeth operators work 11-hour shifts. Chula Vista operators have processed 10,000+ missions over four years, developing automatic (and potentially biased) threat evaluation. The cognitive limitations are universal.</p>
          </div>
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-semibold text-dark mb-1">Governance lags behind deployment</h3>
            <p className="text-sm text-muted leading-relaxed">Elizabeth has the strongest governance framework. Cincinnati has quantitative evidence of spatial concentration (45% of flights clustered near downtown). No city has community perception data. The technology is outpacing accountability structures.</p>
          </div>
        </div>
      </section>

      {/* Program Comparison */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Program Comparison</h2>
        <div className="bg-white rounded-lg border border-border p-4 mb-4">
          <DfrComparisonChart data={dfrData as any} />
        </div>
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="text-left p-3 font-medium text-muted">City</th>
                  <th className="text-left p-3 font-medium text-muted">Vendor</th>
                  <th className="text-right p-3 font-medium text-muted">Fleet</th>
                  <th className="text-right p-3 font-medium text-muted">Missions</th>
                  <th className="text-right p-3 font-medium text-muted">Avg Response</th>
                  <th className="text-right p-3 font-medium text-muted">Success Rate</th>
                </tr>
              </thead>
              <tbody>
                {(dfrData as any[]).map((row) => (
                  <tr key={row.city} className="border-b border-border hover:bg-gray-50">
                    <td className="p-3 font-medium text-dark">{row.city}, {row.state}</td>
                    <td className="p-3 text-muted">{row.vendor}</td>
                    <td className="p-3 text-right text-muted">{row.fleet_size || '—'}</td>
                    <td className="p-3 text-right text-muted">{row.total_missions ? row.total_missions.toLocaleString() : '—'}</td>
                    <td className="p-3 text-right text-muted">{row.avg_response_time_sec ? `${Math.round(row.avg_response_time_sec)}s` : '—'}</td>
                    <td className="p-3 text-right text-muted">
                      {row.successful_missions && row.total_missions
                        ? `${((row.successful_missions / row.total_missions) * 100).toFixed(0)}%`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Cognitive Framework */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">Cognitive Science Findings</h2>
        <p className="text-xs text-muted mb-4">Each row applies a cognitive theory to drone operations across the three cities.</p>
        <div className="space-y-3">
          {(cogSciData as any[]).map((row) => (
            <div key={row.cognitive_dimension} className="bg-white rounded-lg border border-border p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${row.data_quality === 'strong' ? 'bg-green' : 'bg-orange'}`} />
                <span className="text-sm font-semibold text-dark">{row.cognitive_dimension}</span>
                <span className="text-xs text-muted ml-auto">{row.data_quality === 'strong' ? 'Strong evidence' : 'Moderate evidence'}</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">{row.cross_city_assessment}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Prediction Status */}
      <section>
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-2">Prediction Status</h2>
        <p className="text-xs text-muted mb-4">{supported} of {total} cognitive science predictions confirmed by operational data. Remaining {total - supported} require additional data collection.</p>
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="text-left p-3 font-medium text-muted w-8">#</th>
                  <th className="text-left p-3 font-medium text-muted">Prediction</th>
                  <th className="text-left p-3 font-medium text-muted">Theory</th>
                  <th className="text-center p-3 font-medium text-muted w-24">Status</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkData.map((row, i) => (
                  <tr key={i} className="border-b border-border hover:bg-gray-50">
                    <td className="p-3 text-muted">{i + 1}</td>
                    <td className="p-3 text-dark text-xs leading-snug">{row.prediction}</td>
                    <td className="p-3 text-muted text-xs">{row.dimension}</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        row.status === 'supported' ? 'bg-green/10 text-green' :
                        row.status === 'refuted' ? 'bg-red/10 text-red' :
                        row.status === 'pending' ? 'bg-orange/10 text-orange' :
                        'bg-gray-100 text-muted'
                      }`}>
                        {row.status === 'supported' ? 'Confirmed' : row.status === 'pending' ? 'Pending data' : row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
