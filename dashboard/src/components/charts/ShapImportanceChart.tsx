'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { THESIS_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface ShapImportance {
  feature: string;
  importance: number;
}

export default function ShapImportanceChart({ data }: { data: ShapImportance[] }) {
  const sorted = [...data].sort((a, b) => a.importance - b.importance);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={sorted} layout="vertical" margin={{ ...CHART_CONFIG.margin, left: 120 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} horizontal={false} />
        <XAxis type="number" tick={{ fontSize: CHART_CONFIG.fontSize }} />
        <YAxis
          dataKey="feature"
          type="category"
          tick={{ fontSize: 11 }}
          width={110}
        />
        <Tooltip contentStyle={CHART_CONFIG.tooltipStyle} />
        <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
          {sorted.map((entry) => (
            <Cell
              key={entry.feature}
              fill={entry.feature === 'post_rtcc' ? THESIS_COLORS.red : THESIS_COLORS.blue}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
