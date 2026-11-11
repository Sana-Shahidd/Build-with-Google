import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import Home from './pages/Home'
import ReportStatus from './pages/ReportStatus'

// Responder and dashboard pages are lazy-loaded so the reporter bundle stays small on weak phones.
const Responder = lazy(() => import('./pages/Responder'))
const ControlRoom = lazy(() => import('./pages/ControlRoom'))
const Guide = lazy(() => import('./pages/Guide'))
const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Flow = lazy(() => import('./pages/Flow'))
const CardNew = lazy(() => import('./pages/CardNew'))
const CardScan = lazy(() => import('./pages/CardScan'))

const lazyPage = (node: React.ReactNode) => <Suspense fallback={null}>{node}</Suspense>

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/report/:id', element: <ReportStatus /> },
  { path: '/r/:token', element: lazyPage(<Responder />) },
  { path: '/control-room', element: lazyPage(<ControlRoom />) },
  { path: '/guide', element: lazyPage(<Guide />) },
  { path: '/about', element: lazyPage(<Landing />) },
  { path: '/login', element: lazyPage(<Login />) },
  { path: '/dashboard', element: lazyPage(<Dashboard />) },
  { path: '/flow', element: lazyPage(<Flow />) },
  { path: '/card/new', element: lazyPage(<CardNew />) },
  { path: '/c/:token', element: lazyPage(<CardScan />) },
])
