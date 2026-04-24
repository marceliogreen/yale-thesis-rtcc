export function formatPP(value: number): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} pp`;
}

export function formatPValue(p: number): string {
  if (p < 0.001) return 'p < 0.001';
  if (p < 0.01) return `p = ${p.toFixed(3)}`;
  return `p = ${p.toFixed(3)}`;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatPercentRaw(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function significanceLabel(p: number): string {
  if (p < 0.01) return '***';
  if (p < 0.05) return '**';
  if (p < 0.1) return '*';
  return '';
}

export function significanceColor(p: number): string {
  if (p < 0.05) return '#27AE60';
  if (p < 0.1) return '#E67E22';
  return '#7F8C8D';
}
