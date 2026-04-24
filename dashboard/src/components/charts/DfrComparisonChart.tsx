'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { THESIS_COLORS, CHART_CONFIG } from '@/lib/chart-theme';

interface DfrProgram {
  city: string;
  state: string;
  avg_response_time_sec: number;
  total_missions: number;
  fleet_size: number;
  [key: string]: unknown;
}

export default function DfrComparisonChart({ data }: { data: DfrProgram[] }) {
  const chartData = data.map(d => ({
    city: d.city,
    'Avg Response (sec)': d.avg_response_time_sec,
    'Total Missions': d.total_missions,
    'Fleet Size': d.fleet_size,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={chartData} margin={CHART_CONFIG.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CONFIG.gridColor} />
        <XAxis dataKey="city" tick={{ fontSize: CHART_CONFIG.fontSize }} />
        <YAxis tick={{ fontSize: CHART_CONFIG.fontSize }} />
        <Tooltip contentStyle={CHART_CONFIG.tooltipStyle} />
        <Legend />
        <Bar dataKey="Avg Response (sec)" fill={THESIS_COLORS.blue} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Total Missions" fill={THESIS_COLORS.orange} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Fleet Size" fill={THESIS_COLORS.green} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
