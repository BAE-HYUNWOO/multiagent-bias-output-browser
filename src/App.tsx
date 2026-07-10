import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import DatasetPage from './pages/DatasetPage'
import CategoryPage from './pages/CategoryPage'
import ProblemPage from './pages/ProblemPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dataset/:datasetId" element={<DatasetPage />} />
        <Route
          path="/dataset/:datasetId/category/:categorySlug"
          element={<CategoryPage />}
        />
        <Route
          path="/dataset/:datasetId/category/:categorySlug/problem/:pairKey"
          element={<ProblemPage />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}
