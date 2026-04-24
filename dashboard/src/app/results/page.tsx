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
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-2xl font-semibold text-yale mb-2">Results Explorer</h1>
      <p className="text-sm text-muted mb-8 max-w-3xl">
        Interactive visualizations of Study 1 analysis results. Each chart shows a different angle on the same question: did RTCCs improve homicide clearance?
      </p>

      {/* Headline */}
      <section className="mb-10">
        <div className="bg-white rounded-lg border-l-4 border-red border border-border p-5">
          <div className="text-xs text-muted uppercase tracking-wide">Primary Estimate</div>
          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-3xl font-bold text-red">-10.0 pp</span>
            <span className="text-sm text-muted">p = 0.008</span>
          </div>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Cities that adopted RTCCs solved <strong className="text-dark">10 fewer homicides per 100</strong> after adoption, compared to similar cities without RTCCs. This result is statistically significant — the probability of seeing this effect by chance is less than 1%.
          </p>
        </div>
      </section>

      {/* Tab Bar */}
      <div className="flex gap-1 overflow-x-auto border-b border-border mb-6">
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
      <div className="bg-white rounded-lg border border-border p-6">
        {activeTab === 'Clearance Trends' && (
          <>
            <h2 className="text-sm font-semibold text-dark mb-1">Homicide Clearance Rate Trends</h2>
            <p className="text-xs text-muted mb-4">Annual clearance rates by treatment city. Each line shows how often homicides were solved that year.</p>
            <ClearanceTrendsChart data={clearanceRates as any} />
          </>
        )}

        {activeTab === 'Event Study' && (
          <>
            <h2 className="text-sm font-semibold text-dark mb-1">Event Study Trajectories</h2>
            <p className="text-xs text-muted mb-4">Clearance rates relative to the year each city adopted RTCCs (year 0). If RTCCs helped, lines should rise after year 0.</p>
            <EventStudyChart data={eventStudyCoeffs as any} />
          </>
        )}

        {activeTab === 'ITS Forest Plot' && (
          <>
            <h2 className="text-sm font-semibold text-dark mb-1">Interrupted Time Series — Level Change by City</h2>
            <p className="text-xs text-muted mb-4">Each bar shows how much clearance rates changed after RTCC adoption in that city. Bars crossing zero mean no detectable change. Red = statistically significant decline.</p>
            <ItsForestPlot data={extendedIts as any} />
          </>
        )}

        {activeTab === 'SHAP Importance' && (
          <>
            <h2 className="text-sm font-semibold text-dark mb-1">What Actually Predicts Clearance Rates?</h2>
            <p className="text-xs text-muted mb-4">A machine learning model ranked every factor by how much it predicts clearance outcomes. The RTCC adoption variable (red bar) is near the bottom — staffing levels and budget matter far more.</p>
            <ShapImportanceChart data={shapData as any} />
          </>
        )}

        {activeTab === 'Robustness' && (
          <>
            <h2 className="text-sm font-semibold text-dark mb-1">Robustness Checks — Does the Result Hold Up?</h2>
            <p className="text-xs text-muted mb-4">Every dot is a different statistical test. If RTCCs helped, dots should be to the right of zero. They are all to the left — no method finds a positive effect.</p>
            <RobustnessSummaryChart data={robustnessSpecs as any} />
          </>
        )}
      </div>

      {/* All Estimates — Plain Language */}
      <section className="mt-10">
        <h2 className="text-sm font-semibold text-dark uppercase tracking-wide mb-4">All Estimates — What They Mean</h2>
        <div className="space-y-3">
          {[
            { label: 'PSM-DiD (primary)', value: '-10.0 pp', p: 'p = 0.008', meaning: 'The main finding. Matched similar cities with and without RTCCs, then compared before/after. Clearance rates dropped 10 percentage points.' },
            { label: 'Monte Carlo simulation', value: '-17.7 pp', p: 'Bootstrap mean', meaning: 'Ran 10,000 simulated scenarios. The average estimated decline was even larger than the primary estimate.' },
            { label: 'Extended ITS (15 cities)', value: '-0.178', p: 'p = 0.606', meaning: 'A broader model with more cities. The direction is the same (negative) but not statistically significant — the effect varies by city.' },
            { label: 'XGBoost feature importance', value: '0.002', p: 'Minimal', meaning: 'When a machine learning model predicts clearance outcomes, RTCC adoption barely registers. Staffing and budget are 30x more predictive.' },
            { label: 'Pre-COVID reversal', value: '+0.49 pp', p: 'p = 0.012', meaning: 'Before 2019, clearance rates were slightly improving year-over-year. The COVID pandemic disrupted policing, confounding results for cities that adopted after 2017.' },
            { label: 'LASSO regression', value: '-0.0', p: 'Regularized to zero', meaning: 'A statistical method that automatically removes unimportant variables zeroed out RTCC entirely — it found no meaningful effect.' },
          ].map(est => (
            <div key={est.label} className="bg-white rounded-lg border border-border p-4">
              <div className="flex items-baseline gap-3 mb-1">
                <span className="text-xs text-muted uppercase tracking-wide">{est.label}</span>
                <span className="text-lg font-bold text-dark">{est.value}</span>
                <span className="text-xs text-muted">{est.p}</span>
              </div>
              <p className="text-sm text-muted leading-snug">{est.meaning}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
