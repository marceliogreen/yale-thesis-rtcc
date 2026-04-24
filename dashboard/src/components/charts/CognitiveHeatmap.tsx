'use client';

import { THESIS_COLORS } from '@/lib/chart-theme';

interface CognitiveDimension {
  cognitive_dimension: string;
  key_theory?: string;
  key_author?: string;
  chula_vista_finding: string;
  elizabeth_finding: string;
  cincinnati_finding?: string;
  cross_city_assessment: string;
  data_quality: string;
}

const qualityColors: Record<string, string> = {
  strong: '#27AE60',
  moderate: '#E67E22',
  limited: '#F39C12',
  pending: '#BDC3C7',
};

interface Props {
  data: CognitiveDimension[];
}

export default function CognitiveHeatmap({ data }: Props) {
  const cities = ['Chula Vista', 'Elizabeth', 'Cincinnati'] as const;
  const cityKeys = ['chula_vista_finding', 'elizabeth_finding', 'cincinnati_finding'] as const;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th className="text-left p-3 border-b border-border font-serif font-bold text-dark w-48">Cognitive Dimension</th>
            {cities.map(city => (
              <th key={city} className="p-3 border-b border-border font-serif font-bold text-dark text-center">{city}</th>
            ))}
            <th className="p-3 border-b border-border font-serif font-bold text-dark text-center w-24">Data Quality</th>
          </tr>
        </thead>
        <tbody>
          {data.map((dim) => (
            <tr key={dim.cognitive_dimension} className="hover:bg-gray-50 transition-colors">
              <td className="p-3 border-b border-border font-medium text-dark text-xs">
                {dim.cognitive_dimension}
              </td>
              {cityKeys.map((key) => {
                const finding = dim[key];
                if (!finding) return <td key={key} className="p-3 border-b border-border text-center text-xs text-muted">N/A</td>;
                return (
                  <td
                    key={key}
                    className="p-3 border-b border-border text-center text-xs"
                    style={{ backgroundColor: `${qualityColors[dim.data_quality] || '#ECF0F1'}15` }}
                  >
                    <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: qualityColors[dim.data_quality] || '#ECF0F1' }} />
                    {finding.length > 60 ? finding.slice(0, 57) + '...' : finding}
                  </td>
                );
              })}
              <td className="p-3 border-b border-border text-center">
                <span
                  className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                  style={{
                    backgroundColor: `${qualityColors[dim.data_quality] || '#ECF0F1'}20`,
                    color: qualityColors[dim.data_quality] || '#7F8C8D',
                  }}
                >
                  {dim.data_quality}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
