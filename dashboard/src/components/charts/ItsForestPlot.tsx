'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ErrorBar } from 'recharts';
import { THESIS_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface ItsResult {
  city: string;
  level_change: number;
  level_change_se: number;
  level_change_p: number;
  specification: string;
}

export default function ItsForestPlot({ data }: { data: ItsResult[] }) {
  // One entry per city (use the primary specification if multiple exist)
  const cityMap = new Map<string, ItsResult>();
  data.forEach(d => {
    if (!cityMap.has(d.city)) cityMap.set(d.city, d);
  });

  const chartData = [...cityMap.values()]
    .sort((a, b) => a.level_change - b.level_change)
    .map(d => ({
      city: d.city,
      estimate: d.level_change,
      errorX: Math.abs(d.level_change_se * 1.96),
      p: d.level_change_p,
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 45 + 60)}>
      <BarChart data={chartData} layout="vertical" margin={{ ...CHART_CONFIG.margin, left: 100 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={(v: number) => `${v.toFixed(2)}`}
          tick={{ fontSize: CHART_CONFIG.fontSize }}
          label={{ value: 'Level Change (clearance rate)', position: 'insideBottom', offset: -5, style: { fontSize: 12 } }}
        />
        <YAxis dataKey="city" type="category" tick={{ fontSize: 12 }} width={90} />
        <Tooltip
          formatter={(value: number, name: string) => [value?.toFixed(3), name]}
          contentStyle={CHART_CONFIG.tooltipStyle}
        />
        <Bar dataKey="estimate" radius={[0, 4, 4, 0]}>
          <ErrorBar dataKey="errorX" width={4} strokeWidth={1.5} direction="x" />
          {chartData.map((entry) => (
            <Cell
              key={entry.city}
              fill={entry.p < 0.05 ? THESIS_COLORS.red : THESIS_COLORS.blue}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
