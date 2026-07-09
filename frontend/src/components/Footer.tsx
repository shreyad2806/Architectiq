import { Box } from 'lucide-react'

const columns = [
  {
    heading: 'Product',
    links: ['Architecture Audit', 'Cost Intelligence', 'How It Works'],
  },
  {
    heading: 'Developers',
    links: ['Documentation', 'API Reference', 'GitHub'],
  },
  {
    heading: 'Company',
    links: ['Contact', 'Careers', 'Blog'],
  },
]

export default function Footer() {
  return (
    <footer className="border-t border-white/5 bg-[#05070d]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-10 py-14 lg:grid-cols-2">
          {/* Brand */}
          <div>
            <a href="#" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#6d5ce7]">
                <Box className="h-4 w-4 text-white" />
              </span>
              <span className="text-[15px] font-semibold tracking-tight text-white">
                ArchitectIQ
              </span>
            </a>
            <p className="mt-4 max-w-xs text-[13px] leading-relaxed text-slate-500">
              AI architecture intelligence and cost optimization for teams shipping
              production AI systems.
            </p>
          </div>

          {/* Link columns */}
          <div className="grid grid-cols-3 gap-8">
            {columns.map((col) => (
              <div key={col.heading}>
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  {col.heading}
                </p>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-[13px] text-slate-400 transition-colors hover:text-white"
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col items-start justify-between gap-3 border-t border-white/5 py-6 sm:flex-row sm:items-center">
          <p className="text-[12px] text-slate-600">
            © 2026 ArchitectIQ. All rights reserved.
          </p>
          <p className="font-mono text-[12px] text-slate-600">
            v1.x.x — audit online
          </p>
        </div>
      </div>
    </footer>
  )
}
