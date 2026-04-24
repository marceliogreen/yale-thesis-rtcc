export default function Footer() {
  return (
    <footer className="border-t border-border bg-white mt-12">
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-2 text-xs text-muted">
          <span>Marcel J. Green &middot; Yale University &middot; Cognitive Science &middot; 2026</span>
          <a
            href="https://github.com/greenmagic6/yale-thesis-rtcc"
            target="_blank"
            rel="noopener noreferrer"
            className="text-yale hover:underline"
          >
            GitHub Repository
          </a>
        </div>
      </div>
    </footer>
  );
}
