'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { THESIS_COLORS, CITY_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface ClearanceRecord {
  city: string;
  year: number;
  homicides: number;
  cleared: number;
  clearance_rate: number;
  rtcc_year: number;
  post_rtcc: number;
}

interface Props {
  data: ClearanceRecord[];
  cities?: string[];
}

export default function ClearanceTrendsChart({ data, cities }: Props) {
  const selectedCities = cities || Object.keys(CITY_COLORS);
  const filtered = data.filter(d => selectedCities.includes(d.city));

  // Pivot data: one entry per year, each city as a key
  const years = [...new Set(filtered.map(d => d.year))].sort();
  const pivoted = years.map(year => {
    const entry: Record<string, unknown> = { year };
    filtered.filter(d => d.year === year).forEach(d => {
      entry[d.city] = d.clearance_rate;
      if (!entry[`${d.city}_rtcc`]) entry[`${d.city}_rtcc`] = d.rtcc_year;
    });
    return entry;
  });

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={pivoted} margin={CHART_CONFIG.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} />
        <XAxis dataKey="year" tick={{ fontSize: CHART_CONFIG.fontSize }} />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: CHART_CONFIG.fontSize }}
          label={{ value: 'Clearance Rate (%)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
        />
        <Tooltip
          formatter={(value: number, name: string) => [`${value?.toFixed(1)}%`, name]}
          contentStyle={CHART_CONFIG.tooltipStyle}
        />
        <Legend />
        {selectedCities.map(city => (
          <Line
            key={city}
            type="monotone"
            dataKey={city}
            stroke={CITY_COLORS[city] || THESIS_COLORS.gray}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
