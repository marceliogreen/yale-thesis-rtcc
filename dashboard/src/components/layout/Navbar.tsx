'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', label: 'Home' },
  { href: '/study1', label: 'Study 1' },
  { href: '/results', label: 'Results' },
  { href: '/study2', label: 'Study 2' },
  { href: '/methodology', label: 'Methodology' },
  { href: '/appendix', label: 'Appendix' },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-border">
      <div className="max-w-5xl mx-auto px-6">
        <div className="flex items-center justify-between h-14">
          <Link href="/" className="text-sm font-semibold text-yale tracking-tight">
            RTCC Thesis
          </Link>
          <div className="hidden md:flex items-center gap-0.5">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded text-sm ${
                  pathname === item.href
                    ? 'text-yale font-medium bg-yale/5'
                    : 'text-muted hover:text-dark'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="md:hidden flex items-center gap-0.5 overflow-x-auto">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-2 py-1 rounded text-xs whitespace-nowrap ${
                  pathname === item.href
                    ? 'text-yale font-medium bg-yale/5'
                    : 'text-muted'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}
