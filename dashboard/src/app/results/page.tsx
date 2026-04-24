'use client';

import { useState } from 'react';
import ClearanceTrendsChart from '@/components/charts/ClearanceTrendsChart';
import EventStudyChart from '@/components/charts/EventStudyChart';
import ShapImportanceChart from '@/components/charts/ShapImportanceChart';
import ItsForestPlot from '@/components/charts/ItsForestPlot';
import RobustnessSummaryChart from '@/components/charts/RobustnessSummaryChart';

import clearanceRates from '@/data/study1/clearance_rates.json';
import eventStudyCoeffs from '@/data/study1/event_study_coefficients.json';
import shapData from '@/data/study1/shap_importance.json';
import extendedIts from '@/data/study1/extended_its.json';
import robustnessSpecs from '@/data/study1/robustness_specs.json';

const TABS = ['Clearance Trends', 'Event Study', 'ITS Forest Plot', 'SHAP Importance', 'Robustness'] as const;
type Tab = typeof TABS[number];

export default function ResultsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('Clearance Trends');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-serif font-bold text-yale mb-2">Results Explorer</h1>
      <p className="text-muted mb-8 max-w-3xl">
        Interactive visualizations of Study 1 analysis results. Select a tab to explore different analytical perspectives.
      </p>

      {/* Tab Bar */}
      <div className="flex gap-1 overflow-x-auto border-b border-border mb-8">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-yale text-yale'
                : 'border-transparent text-muted hover:text-dark'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Chart Area */}
      <div className="bg-white rounded-xl border border-border p-6">
        {activeTab === 'Clearance Trends' && (
          <>
            <h2 className="text-lg font-serif font-bold text-dark mb-1">Homicide Clearance Rate Trends</h2>
            <p className="text-xs text-muted mb-6">Annual clearance rates by treatment city, 2007–2017. Vertical markers indicate RTCC adoption year.</p>
            <ClearanceTrendsChart data={clearanceRates as any} />
          </>
        )}

        {activeTab === 'Event Study' && (
          <>
            <h2 className="text-lg font-serif font-bold text-dark mb-1">Event Study Trajectories</h2>
            <p className="text-xs text-muted mb-6">Mean clearance rate relative to RTCC adoption year (year 0). Reference period highlighted.</p>
            <EventStudyChart data={eventStudyCoeffs as any} />
          </>
        )}

        {activeTab === 'ITS Forest Plot' && (
          <>
            <h2 className="text-lg font-serif font-bold text-dark mb-1">Extended ITS — Level Change by City</h2>
            <p className="text-xs text-muted mb-6">Interrupted time series level change estimates with 95% CIs. Red = significant at p &lt; 0.05.</p>
            <ItsForestPlot data={extendedIts as any} />
          </>
        )}

        {activeTab === 'SHAP Importance' && (
          <>
            <h2 className="text-lg font-serif font-bold text-dark mb-1">XGBoost SHAP Feature Importance</h2>
            <p className="text-xs text-muted mb-6">Mean absolute SHAP values from XGBoost classifier predicting post-RTCC clearance outcomes. The post_rtcc feature (red) shows minimal predictive importance.</p>
            <ShapImportanceChart data={shapData as any} />
          </>
        )}

        {activeTab === 'Robustness' && (
          <>
            <h2 className="text-lg font-serif font-bold text-dark mb-1">Robustness Specification Summary</h2>
            <p className="text-xs text-muted mb-6">Point estimates from all robustness specifications. No specification produces a statistically significant positive effect.</p>
            <RobustnessSummaryChart data={robustnessSpecs as any} />
          </>
        )}
      </div>

      {/* Key Estimates */}
      <section className="mt-8">
        <h2 className="text-xl font-serif font-bold text-dark mb-4">Key Estimates</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { label: 'PSM-DiD ATT', value: '\u221210.0 pp', p: 'p = 0.008', desc: 'Primary estimate, propensity-score matched' },
            { label: 'Monte Carlo Mean', value: '\u221217.7 pp', p: 'Bootstrap', desc: '10,000-iteration parametric bootstrap' },
            { label: 'ITS Pooled Level Change', value: '\u22120.178', p: 'p = 0.606', desc: 'Bayesian ITS hierarchical estimate' },
            { label: 'XGBoost SHAP (post_rtcc)', value: '0.002', p: 'Minimal', desc: 'Feature importance for RTCC treatment indicator' },
            { label: 'Pre-COVID Reversal', value: '+0.49 pp', p: 'p = 0.012', desc: 'Year-over-year trend change after 2019' },
            { label: 'LASSO RTCC Coefficient', value: '\u22120.0', p: 'Regularized', desc: 'L1 penalty zeros out RTCC effect entirely' },
          ].map(est => (
            <div key={est.label} className="bg-white rounded-lg border border-border p-4">
              <div className="text-xs text-muted uppercase tracking-wide mb-1">{est.label}</div>
              <div className="text-2xl font-bold text-dark">{est.value}</div>
              <div className="text-xs font-medium text-muted">{est.p}</div>
              <div className="text-xs text-muted mt-1">{est.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
