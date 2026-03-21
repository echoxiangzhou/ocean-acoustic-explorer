import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { GlobalOverview } from './modules/global-overview/GlobalOverview'
import { ProfileBrowser } from './modules/profile-browser/ProfileBrowser'
import { SectionAnalysis } from './modules/section-analysis/SectionAnalysis'
import { TrendAnalysis } from './modules/trend-analysis/TrendAnalysis'
import { ScenarioSim } from './modules/scenario-sim/ScenarioSim'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<GlobalOverview />} />
          <Route path="/profiles" element={<ProfileBrowser />} />
          <Route path="/analysis" element={<SectionAnalysis />} />
          <Route path="/trends" element={<TrendAnalysis />} />
          <Route path="/scenarios" element={<ScenarioSim />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
