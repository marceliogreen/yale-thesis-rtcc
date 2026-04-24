const METHODS = [
  {
    name: 'Bayesian Interrupted Time Series',
    desc: 'Hierarchical partial-pooling model with city-specific intercepts, slopes, and treatment effects. MCMC estimation via PyMC with 4 chains, 2000 draws each, random seeds [1,2,3,4].',
    spec: 'Y_ct = \u03B1c + \u03B21c \u00B7 Time + \u03B22c \u00B7 Postt + \u03B23c \u00B7 Time \u00D7 Postt + \u03B5ct',
    assumptions: ['Parallel pre-trends across treatment and comparison', 'No contemporaneous shocks confounding the intervention', 'Correct specification of the underlying trend'],
  },
  {
    name: 'Propensity-Score Matched DiD',
    desc: 'Nearest-neighbor matching on population, sworn officers, region, and pre-treatment clearance rates. Difference-in-differences on the matched sample.',
    spec: 'ATT = E[Y(1) \u2212 Y(0) | D=1] estimated via OLS on matched pairs',
    assumptions: ['Conditional independence assumption (unconfoundedness)', 'Overlap: positive probability of treatment for all covariate values', 'Stable unit treatment value (no spillovers)'],
  },
  {
    name: 'Monte Carlo Bootstrap',
    desc: '10,000-iteration parametric bootstrap drawing treatment effects from the fitted aggregate distribution. Uses numpy.random.default_rng(42) for reproducibility.',
    spec: '\u03B8\u0302* = bootstrap(\u03B1, \u03B2, \u03C3\u00B2 | data), reporting E[\u03B8\u0302*] and 95% CI',
    assumptions: ['Parametric model correctly specifies the data-generating process', 'Bootstrap distribution approximates the sampling distribution'],
  },
  {
    name: 'Prophet Counterfactual',
    desc: 'Facebook Prophet time-series forecasting trained on pre-RTCC data. Generates counterfactual post-RTCC clearance trajectories for each treated city.',
    spec: 'y(t) = g(t) + s(t) + h(t) + \u03B5t where g=trend, s=seasonality, h=holidays',
    assumptions: ['Pre-intervention trend continues absent treatment', 'Seasonal patterns remain stable'],
  },
  {
    name: 'XGBoost + SHAP',
    desc: 'Gradient-boosted decision tree classifier predicting post-RTCC clearance outcomes. SHAP (SHapley Additive exPlanations) values quantify each feature\'s contribution, including the post_rtcc treatment indicator.',
    spec: 'F(x) = \u03A3 fk(x) with SHAP: \u03C6i = E[f(x) | xi] \u2212 E[f(x)]',
    assumptions: ['Feature importance reflects predictive power, not necessarily causation', 'Model specification captures relevant non-linearities'],
  },
  {
    name: 'Causal Forest (EconML)',
    desc: 'CausalForestDML from Microsoft\'s EconML library. Estimates heterogeneous treatment effects (CATE) conditional on city-level covariates.',
    spec: '\u03C4(x) = E[Y(1) \u2212 Y(0) | X=x] estimated via honest splitting',
    assumptions: ['Unconfoundedness conditional on X', 'Overlap in covariate distributions', 'No unmeasured effect modifiers'],
  },
  {
    name: 'Event Study Diagnostics',
    desc: 'Year-by-year clearance rate trajectories relative to RTCC adoption (event time). Tests for pre-trends and dynamic treatment effects.',
    spec: 'Yct = \u03B1c + \u03B3t + \u03A3\u03C4 \u03B2\u03C4 \u00B7 1(t \u2212 T*c = \u03C4) + \u03B5ct',
    assumptions: ['No anticipatory effects (pre-treatment coefficients should be zero)', 'Treatment timing is exogenous conditional on controls'],
  },
  {
    name: 'Robustness Suite (10 Specifications)',
    desc: 'Battery of robustness checks: COVID-weighted binomial, logit specification, contaminated controls, Fresno exclusion, mediator analysis, extended 15-city ITS, ML pipeline comparison, and more.',
    spec: 'Multiple specifications varying: sample, functional form, matching algorithm, control set',
    assumptions: ['If the result is robust across specifications, it is less likely to be an artifact of any single modeling choice'],
  },
];

export default function MethodologyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-serif font-bold text-yale mb-2">Methodology</h1>
      <p className="text-muted mb-8">
        Study 1 employs six complementary causal inference methods, each with distinct assumptions, verified through 10 robustness specifications.
      </p>

      <div className="space-y-4">
        {METHODS.map((method) => (
          <details key={method.name} className="bg-white rounded-xl border border-border group">
            <summary className="p-6 cursor-pointer flex items-center justify-between">
              <h2 className="text-lg font-serif font-bold text-dark group-open:text-yale">{method.name}</h2>
              <svg className="w-5 h-5 text-muted group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="px-6 pb-6 border-t border-border pt-4">
              <p className="text-sm text-muted leading-relaxed mb-4">{method.desc}</p>
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <div className="text-xs text-muted mb-1 font-medium">Formal Specification</div>
                <code className="text-sm text-dark">{method.spec}</code>
              </div>
              <div>
                <div className="text-xs text-muted mb-2 font-medium uppercase tracking-wide">Key Assumptions</div>
                <ul className="text-xs text-muted space-y-1">
                  {method.assumptions.map((a, i) => (
                    <li key={i} className="flex gap-2"><span className="text-yale">&#8226;</span> {a}</li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
