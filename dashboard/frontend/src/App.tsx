import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import ResourceExplorer from './pages/ResourceExplorer';
import {
  ArchitectureViewer,
  CostAnalysis,
  DeploymentManager,
  Monitoring,
  Settings,
} from './pages/stubs';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/architecture" element={<ArchitectureViewer />} />
            <Route path="/resources" element={<ResourceExplorer />} />
            <Route path="/cost" element={<CostAnalysis />} />
            <Route path="/deployment" element={<DeploymentManager />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App;
