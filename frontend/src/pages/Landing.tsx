import Navbar from '../components/Navbar'
import Hero from '../components/Hero'
import DashboardPreview from '../components/DashboardPreview'
import Features from '../components/Features'
import Process from '../components/Process'
import CTA from '../components/CTA'
import Footer from '../components/Footer'

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#05070d] antialiased">
      <Navbar />
      <main>
        <Hero />
        <DashboardPreview />
        <Features />
        <Process />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
