import KeyFindingCard from '@/components/ui/KeyFindingCard';
import Link from 'next/link';

const KEY_FINDINGS = [
  {
    label: 'PSM-DiD Estimate',
    value: '\u221210.0 pp',
    significance: 'p = 0.008',
    description: 'Propensity-score matched difference-in-differences estimate of RTCC effect on homicide clearance rates across 8 treatment cities.',
    color: 'red' as const,
  },
  {
    label: 'Monte Carlo Bootstrap',
    value: '\u221217.7 pp',
    significance: 'Parametric bootstrap mean',
    description: 'Average treatment effect from 10,000 bootstrap iterations.',
    color: 'orange' as const,
  },
  {
    label: 'Pre-COVID Reversal',
    value: '+0.49 pp',
    significance: 'p = 0.012',
    description: 'Year-over-year clearance trend reversal after 2019, suggesting COVID-era confounding.',
    color: 'green' as const,
  },
  {
    label: 'Cognitive Predictions',
    value: '16 / 18',
    significance: 'Supported by operational data',
    description: 'Cross-city cognitive science predictions confirmed across detection, comprehension, and procedural justice dimensions.',
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

      {/* Abstract */}
      <section className="max-w-3xl mx-auto mb-14">
        <div className="bg-white rounded-lg border border-border p-6">
          <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-3">Abstract</h2>
          <p className="text-sm text-muted leading-relaxed">
            Real-Time Crime Centers (RTCCs) integrate surveillance feeds, gunshot detection, license plate readers, and predictive algorithms into centralized analyst workstations. This thesis evaluates whether RTCC adoption improves homicide clearance rates across eight U.S. cities using Bayesian interrupted time series, propensity-score matched difference-in-differences, Monte Carlo simulation, Prophet counterfactuals, XGBoost with SHAP explanation, and causal forests. The primary PSM-DiD estimate finds a significant negative treatment effect of &minus;10.0 percentage points (p&thinsp;=&thinsp;0.008), and no specification produces a statistically significant positive effect. A parallel cognitive science framework evaluates drone-as-first-responder programs across three cities, finding that 16 of 18 cognitive predictions are supported by operational data.
          </p>
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
          <h3 className="text-sm font-semibold text-yale uppercase tracking-wide mb-3">Study 1 &mdash; RTCC Effectiveness</h3>
          <ul className="text-sm text-muted space-y-1.5">
            <li><strong className="text-dark">8</strong> treatment cities with verified RTCC dates</li>
            <li><strong className="text-dark">371</strong> comparison cities (100K&ndash;300K population)</li>
            <li><strong className="text-dark">6</strong> causal inference methods, <strong className="text-dark">10</strong> robustness checks</li>
            <li>UCR Return A data, 2007&ndash;2024</li>
          </ul>
        </div>
        <div className="bg-white rounded-lg border border-border p-6">
          <h3 className="text-sm font-semibold text-yale uppercase tracking-wide mb-3">Study 2 &mdash; DFR + Cognitive Science</h3>
          <ul className="text-sm text-muted space-y-1.5">
            <li><strong className="text-dark">3</strong> drone-as-first-responder programs</li>
            <li><strong className="text-dark">6</strong> cognitive dimensions, <strong className="text-dark">18</strong> predictions</li>
            <li>Chula Vista CA, Elizabeth NJ, Cincinnati OH</li>
            <li>Operational data + cognitive framework</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
