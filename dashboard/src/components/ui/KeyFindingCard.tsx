interface KeyFindingCardProps {
  label: string;
  value: string;
  significance: string;
  description: string;
  color: 'blue' | 'red' | 'orange' | 'green';
}

const borderMap = {
  blue: 'border-yale',
  red: 'border-red',
  orange: 'border-orange',
  green: 'border-green',
};

const bgMap = {
  blue: 'bg-yale',
  red: 'bg-red',
  orange: 'bg-orange',
  green: 'bg-green',
};

export default function KeyFindingCard({ label, value, significance, description, color }: KeyFindingCardProps) {
  return (
    <div className={`rounded-lg border-l-4 ${borderMap[color]} bg-white p-4 border border-border`}>
      <span className="text-xs font-medium text-muted uppercase tracking-wide">{label}</span>
      <div className="text-2xl font-bold text-dark mt-1 mb-0.5">{value}</div>
      <div className="text-xs font-medium mb-1.5">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${bgMap[color]} mr-1`} />
        {significance}
      </div>
      <p className="text-xs text-muted leading-snug">{description}</p>
    </div>
  );
}
