import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/layout/Navbar';
import Footer from '@/components/layout/Footer';

export const metadata: Metadata = {
  title: 'RTCC Thesis — Evaluating Real-Time Crime Centers',
  description:
    'Interactive results for "Advancing Computational Perception toward Cognitive-Grounded Prediction" by Marcel J. Green, Yale University.',
  openGraph: {
    title: 'RTCC Thesis Dashboard',
    description: 'Multi-method evaluation of Real-Time Crime Centers across 15 cities.',
    type: 'website',
    url: 'https://dashboard-alpha-pearl-55.vercel.app',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
