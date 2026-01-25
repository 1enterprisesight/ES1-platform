import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { BrandingProvider } from './hooks/useBranding';
import {
  Dashboard,
  ResourceRegistry,
  GatewayManager,
  Deployments,
  Activity,
  Settings,
} from './pages';

function App() {
  return (
    <BrandingProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resources" element={<ResourceRegistry />} />
          <Route path="/gateway" element={<GatewayManager />} />
          <Route path="/deployments" element={<Deployments />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </BrandingProvider>
  );
}

export default App;
