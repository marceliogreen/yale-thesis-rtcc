'use client';

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ErrorBar, ReferenceLine, ZAxis } from 'recharts';
import { THESIS_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface EventStudyPoint {
  city: string;
  event_time: number;
  mean_cr: number;
  se: number;
  n: number;
  is_pre: boolean;
  is_reference: boolean;
  rtcc_year: number;
}

interface Props {
  data: EventStudyPoint[];
  city?: string;
}

export default function EventStudyChart({ data, city }: Props) {
  const filtered = city ? data.filter(d => d.city === city) : data;
  const cities = [...new Set(filtered.map(d => d.city))];

  const chartData = filtered.map(d => ({
    x: d.event_time,
    y: d.mean_cr,
    errorY: d.se * 1.96,
    city: d.city,
    is_reference: d.is_reference,
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart margin={CHART_CONFIG.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} />
        <XAxis
          dataKey="x"
          type="number"
          tick={{ fontSize: CHART_CONFIG.fontSize }}
          label={{ value: 'Years from RTCC Adoption', position: 'insideBottom', offset: -5, style: { fontSize: 12 } }}
        />
        <YAxis
          dataKey="y"
          type="number"
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fontSize: CHART_CONFIG.fontSize }}
          label={{ value: 'Mean Clearance Rate (%)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
        />
        <ZAxis range={[40, 40]} />
        <ReferenceLine x={0} stroke={THESIS_COLORS.red} strokeDasharray="5 5" label="RTCC Adoption" />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, name: any, props: any) => [
            `${Number(value)?.toFixed(1)}%`,
            `${props?.payload?.city || ''}${props?.payload?.is_reference ? ' (reference)' : ''}`,
          ]}
          contentStyle={CHART_CONFIG.tooltipStyle}
        />
        {cities.map((c, i) => (
          <Scatter
            key={c}
            name={c}
            data={chartData.filter(d => d.city === c)}
            fill={Object.values(THESIS_COLORS)[i % 6]}
          >
            <ErrorBar dataKey="errorY" width={0} stroke="transparent" />
          </Scatter>
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
  }
