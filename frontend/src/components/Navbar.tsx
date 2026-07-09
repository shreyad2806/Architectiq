import { Box } from 'lucide-react'

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-[#05070d]/90 backdrop-blur">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#6d5ce7]">
              <Box className="h-4 w-4 text-white" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-white">
              ArchitectIQ
            </span>
          </a>

          {/* Nav links */}
          <nav className="hidden items-center gap-8 md:flex">
            <a href="#product" className="text-[13px] text-slate-400 transition-colors hover:text-white">
              Product
            </a>
            <a href="#how-it-works" className="text-[13px] text-slate-400 transition-colors hover:text-white">
              How It Works
            </a>
            <a href="#docs" className="text-[13px] text-slate-400 transition-colors hover:text-white">
              Docs
            </a>
            <a href="#pricing" className="text-[13px] text-slate-400 transition-colors hover:text-white">
              Pricing
            </a>
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <a
              href="#docs"
              className="hidden rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07] sm:inline-block"
            >
              View API Docs
            </a>
            <a
              href="#analyze"
              className="rounded-lg bg-[#6d5ce7] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
            >
              Analyze Architecture
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}
