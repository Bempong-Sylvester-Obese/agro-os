// src/App.jsx
import { useState } from 'react'
import Navbar        from './components/Navbar'
import HomePage      from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage  from './pages/FeaturesPage'
import PricingPage   from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  const [page, setPage] = useState('home')

  return (
    <>
      <Navbar activePage={page} setPage={setPage} />

      {page === 'home'      && <HomePage      setPage={setPage} />}
      {page === 'solutions' && <SolutionsPage setPage={setPage} />}
      {page === 'features'  && <FeaturesPage  setPage={setPage} />}
      {page === 'pricing'   && <PricingPage   setPage={setPage} />}
      {page === 'dashboard' && <DashboardPage />}
    </>
  )
}
