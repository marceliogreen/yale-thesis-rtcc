'use client';

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ZAxis } from 'recharts';
import { THESIS_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface RobustnessSpec {
  specification: string;
  estimate?: number;
  level_change?: number;
  se?: number;
  p_value?: number;
  level_change_p?: number;
  category: string;
  [key: string]: unknown;
}

export default function RobustnessSummaryChart({ data }: { data: RobustnessSpec[] }) {
  const chartData = data.map((d, i) => ({
    name: d.specification,
    x: (d.estimate ?? d.level_change ?? 0) as number,
    y: i,
    p: (d.p_value ?? d.level_change_p ?? 1) as number,
    category: d.category,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 35 + 60)}>
      <ScatterChart margin={{ ...CHART_CONFIG.margin, left: 180 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} horizontal={false} />
        <XAxis
          dataKey="x"
          type="number"
          tick={{ fontSize: CHART_CONFIG.fontSize }}
          label={{ value: 'Estimate (clearance rate change)', position: 'insideBottom', offset: -5, style: { fontSize: 12 } }}
        />
        <YAxis
          dataKey="y"
          type="number"
          tick={false}
          axisLine={false}
          tickLine={false}
        />
        <ZAxis range={[80, 80]} />
        <ReferenceLine x={0} stroke={THESIS_COLORS.dark} strokeWidth={1.5} />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, name: any, props: any) => [
            `${Number(value)?.toFixed(3)} (p=${props?.payload?.p?.toFixed(3) ?? 'N/A'})`,
            props?.payload?.name || '',
          ]}
          contentStyle={CHART_CONFIG.tooltipStyle}
        />
        <Scatter data={chartData}>
          {chartData.map((entry) => (
            <circle
              key={entry.name}
              cx={0} cy={0} r={6}
              fill={entry.p < 0.05 ? THESIS_COLORS.red : THESIS_COLORS.blue}
            />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
