import fs from 'fs';
import path from 'path';
import AppendixContent from './AppendixContent';

export default function AppendixPage() {
  const mdPath = path.resolve(process.cwd(), 'src/data/appendix-code-summary.md');
  let markdown = '*Appendix content not found. Ensure `appendix-code-summary.md` exists at the repository root.*';
  try {
    markdown = fs.readFileSync(mdPath, 'utf-8');
  } catch {
    // File not found — use placeholder
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-serif font-bold text-yale mb-2">Code Appendix</h1>
      <p className="text-muted mb-8">
        Complete code traceability: every script, function, figure, and numerical estimate in the thesis mapped to its source.
      </p>
      <div className="bg-white rounded-xl border border-border p-8 prose prose-sm max-w-none">
        <AppendixContent markdown={markdown} />
      </div>
    </div>
  );
}
