import CognitiveHeatmap from '@/components/charts/CognitiveHeatmap';
import DfrComparisonChart from '@/components/charts/DfrComparisonChart';
import cogSciData from '@/data/study2/cog_sci_comparison.json';
import dfrData from '@/data/study2/dfr_cross_program.json';
import benchmarkData from '@/data/study2/benchmark_mapping.json';

export default function Study2Page() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-serif font-bold text-yale mb-2">Study 2: DFR + Emerging Technology</h1>
      <p className="text-muted mb-8 max-w-3xl">
        Drone-as-first-responder programs evaluated through a cognitive science framework spanning situation awareness, vigilance, automaticity, intent attribution, and procedural justice.
      </p>

      {/* DFR Program Comparison */}
      <section className="mb-12">
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Program Comparison</h2>
        <div className="bg-white rounded-xl border border-border p-6">
          <DfrComparisonChart data={dfrData as any} />
        </div>

        {/* Program Details Table */}
        <div className="mt-4 bg-white rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-border">
                <th className="text-left p-3 font-medium text-muted">City</th>
                <th className="text-left p-3 font-medium text-muted">Vendor</th>
                <th className="text-right p-3 font-medium text-muted">Fleet</th>
                <th className="text-right p-3 font-medium text-muted">Missions</th>
                <th className="text-right p-3 font-medium text-muted">Avg Response</th>
                <th className="text-left p-3 font-medium text-muted">Status</th>
              </tr>
            </thead>
            <tbody>
              {(dfrData as any[]).map((row) => (
                <tr key={row.city} className="border-b border-border hover:bg-gray-50">
                  <td className="p-3 font-medium text-dark">{row.city}, {row.state}</td>
                  <td className="p-3 text-muted">{row.vendor}</td>
                  <td className="p-3 text-right">{row.fleet_size}</td>
                  <td className="p-3 text-right">{row.total_missions?.toLocaleString()}</td>
                  <td className="p-3 text-right">{row.avg_response_time_sec ? `${Math.round(row.avg_response_time_sec)}s` : 'N/A'}</td>
                  <td className="p-3"><span className="text-xs px-2 py-0.5 rounded-full bg-green/10 text-green font-medium">{row.program_status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Cognitive Framework */}
      <section className="mb-12">
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Cognitive Science Framework</h2>
        <p className="text-sm text-muted mb-4">Cross-city comparison of cognitive dimensions applied to drone-as-first-responder operations.</p>
        <div className="bg-white rounded-xl border border-border p-6">
          <CognitiveHeatmap data={cogSciData as any} />
        </div>
      </section>

      {/* Predictions */}
      <section>
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Prediction Status (16/18 Supported)</h2>
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-border">
                <th className="text-left p-3 font-medium text-muted w-8">#</th>
                <th className="text-left p-3 font-medium text-muted">Prediction</th>
                <th className="text-left p-3 font-medium text-muted">Dimension</th>
                <th className="text-center p-3 font-medium text-muted w-24">Status</th>
              </tr>
            </thead>
            <tbody>
              {(benchmarkData as any[]).map((row, i) => (
                <tr key={i} className="border-b border-border hover:bg-gray-50">
                  <td className="p-3 text-muted">{i + 1}</td>
                  <td className="p-3 text-dark">{row.prediction_text || row.prediction || `Prediction ${i + 1}`}</td>
                  <td className="p-3 text-muted text-xs">{row.cognitive_dimension}</td>
                  <td className="p-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      row.status === 'supported' ? 'bg-green/10 text-green' :
                      row.status === 'refuted' ? 'bg-red/10 text-red' :
                      row.status === 'pending' ? 'bg-orange/10 text-orange' :
                      'bg-gray-100 text-muted'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
