import KeyFindingCard from '@/components/ui/KeyFindingCard';
import Link from 'next/link';

const KEY_FINDINGS = [
  {
    label: 'REPRODUCIBILITY NOTE',
    value: 'PSM pending',
    significance: 'missing panel input',
    description: 'The checked-in repo snapshot does not include the exact panel file needed to rerun the original PSM-DiD estimate, so that headline number is currently under-documented.',
    color: 'red' as const,
  },
  {
    label: 'Bootstrap Confirmation',
    value: '\u221217.7 pp',
    significance: '10,000 simulations agree',
    description: 'A 10,000-iteration simulation estimates the average effect could be even worse — a 17.7 percentage point decline.',
    color: 'orange' as const,
  },
  {
    label: 'Weighted ITS Check',
    value: '\u221214.1 pp',
    significance: 'p < 0.001',
    description: 'A homicide-weighted ITS sensitivity still points negative, reinforcing the conclusion that the reproducible evidence in this snapshot does not support a positive RTCC effect.',
    color: 'green' as const,
  },
  {
    label: 'Drone Predictions',
    value: '16 / 18',
    significance: 'Confirmed by real operational data',
    description: 'Cognitive science predictions about drone operator performance were confirmed across 3 cities — operators face vigilance limits and speed-accuracy tradeoffs.',
    color: 'blue' as const,
  },
];

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto px-6">
      {/* Hero */}
      <section className="py-20 text-center">
        <h1 className="text-3xl md:text-4xl font-semibold text-yale leading-tight mb-4 max-w-3xl mx-auto">
          Advancing Computational Perception toward Cognitive-Grounded Prediction
        </h1>
        <p className="text-base text-muted max-w-2xl mx-auto mb-1">
          Evaluating the Efficiency of Real-Time Crime Centers and Emerging Technology
        </p>
        <p className="text-sm text-muted mb-10">
          Marcel J. Green &middot; Yale University &middot; Cognitive Science &middot; 2026
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link href="/results" className="px-5 py-2.5 bg-yale text-white rounded-md text-sm font-medium hover:bg-yale/90 transition-colors">
            Explore Results
          </Link>
          <Link href="/methodology" className="px-5 py-2.5 bg-white text-yale border border-border rounded-md text-sm font-medium hover:bg-gray-50 transition-colors">
            Methodology
          </Link>
          <Link href="/appendix" className="px-5 py-2.5 bg-white text-muted border border-border rounded-md text-sm font-medium hover:bg-gray-50 transition-colors">
            Code Appendix
          </Link>
        </div>
      </section>

      {/* What This Thesis Finds — Plain Language */}
      <section className="max-w-3xl mx-auto mb-14">
        <div className="bg-white rounded-lg border border-border p-6">
          <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-3">What This Thesis Finds</h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>Real-Time Crime Centers (RTCCs) integrate surveillance cameras, gunshot detection, license plate readers, and predictive algorithms into centralized analyst workstations. Over 80 cities have adopted them. The question: do they actually help solve more homicides?</p>
            <p><strong className="text-dark">The answer is still no in the reproducible snapshot.</strong> Across the Study 1 reruns I could execute from the checked-in data, RTCC adoption does not show a statistically significant positive effect on homicide clearance. The Monte Carlo estimate remains strongly negative, and the pooled extended ITS result remains negative as well. The originally cited PSM-DiD headline estimate cannot currently be rerun from this repo alone because the required panel input is missing.</p>
            <p>A second study examines drone-as-first-responder programs in three cities through a cognitive science lens, finding that operators face the same perceptual limitations predicted by decades of laboratory research: attention degrades over time, fast response does not equal accurate understanding, and experience creates automatic but potentially biased threat evaluation.</p>
          </div>
        </div>
      </section>

      {/* Key Findings */}
      <section className="mb-14">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide text-center mb-6">Key Findings</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {KEY_FINDINGS.map((finding) => (
            <KeyFindingCard key={finding.label} {...finding} />
          ))}
        </div>
      </section>

      {/* Study Overview */}
      <section className="grid md:grid-cols-2 gap-4 mb-16">
        <div className="bg-white rounded-lg border border-border p-6">
          <h3 className="text-sm font-semibold text-yale uppercase tracking-wide mb-3">Study 1 — RTCC Effectiveness</h3>
          <ul className="text-sm text-muted space-y-1.5">
            <li><strong className="text-dark">8</strong> cities that adopted RTCCs, compared to <strong className="text-dark">371</strong> similar cities that did not</li>
            <li><strong className="text-dark">6</strong> different statistical methods, all telling the same story</li>
            <li>20 years of FBI homicide data (2007–2024)</li>
          </ul>
        </div>
        <div className="bg-white rounded-lg border border-border p-6">
          <h3 className="text-sm font-semibold text-yale uppercase tracking-wide mb-3">Study 2 — Drones + Cognition</h3>
          <ul className="text-sm text-muted space-y-1.5">
            <li><strong className="text-dark">3</strong> drone-as-first-responder programs studied</li>
            <li><strong className="text-dark">6</strong> cognitive theories tested against real flight data</li>
            <li>Chula Vista CA, Elizabeth NJ, Cincinnati OH</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
