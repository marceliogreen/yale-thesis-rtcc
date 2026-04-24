// Academic chart theme matching thesis palette
export const THESIS_COLORS = {
  blue: '#2E4A7A',
  red: '#C0392B',
  orange: '#E67E22',
  green: '#27AE60',
  gray: '#7F8C8D',
  dark: '#2C3E50',
  lightGray: '#ECF0F1',
  yale: '#00356b',
  background: '#FAFAFA',
  card: '#FFFFFF',
} as const;

export const CHART_CONFIG = {
  margin: { top: 20, right: 30, left: 60, bottom: 40 },
  fontSize: 13,
  fontFamily: 'Inter, system-ui, sans-serif',
  gridColor: '#E5E7EB',
  axisColor: '#6B7280',
  tooltipStyle: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E5E7EB',
    borderRadius: '8px',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
    padding: '12px',
  },
} as const;

// City color mapping for consistent chart rendering
export const CITY_COLORS: Record<string, string> = {
  'Chicago': THESIS_COLORS.blue,
  'Miami': THESIS_COLORS.orange,
  'St. Louis': THESIS_COLORS.red,
  'Newark': THESIS_COLORS.green,
  'New Orleans': '#8E44AD',
  'Albuquerque': '#2980B9',
  'Fresno': THESIS_COLORS.gray,
  'Hartford': '#16A085',
};
