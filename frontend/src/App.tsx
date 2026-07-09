import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Review from './pages/Review'
import Loading from './pages/Loading'
import Report from './pages/Report'
import Docs from './pages/Docs'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/review" element={<Review />} />
        <Route path="/loading" element={<Loading />} />
        <Route path="/report" element={<Report />} />
        <Route path="/docs" element={<Docs />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
