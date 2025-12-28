import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import { Dashboard } from './pages/Dashboard';
import { Subscribers } from './pages/Subscribers';
import { NetworkConfig } from './pages/NetworkConfig';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/subscribers" element={<Subscribers />} />
          <Route path="/network" element={<NetworkConfig />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
