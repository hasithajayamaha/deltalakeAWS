// Stub pages for the dashboard
import { Box, Typography } from '@mui/material';

export const ArchitectureViewer = () => (
  <Box p={3}>
    <Typography variant="h4">Architecture Viewer</Typography>
    <Typography>Interactive visualization of AWS data lake architecture</Typography>
  </Box>
);

export const CostAnalysis = () => (
  <Box p={3}>
    <Typography variant="h4">Cost Analysis</Typography>
    <Typography>Monthly cost breakdown and trends</Typography>
  </Box>
);

export const DeploymentManager = () => (
  <Box p={3}>
    <Typography variant="h4">Deployment Manager</Typography>
    <Typography>Manage deployments and view history</Typography>
  </Box>
);

export const Monitoring = () => (
  <Box p={3}>
    <Typography variant="h4">Monitoring</Typography>
    <Typography>CloudWatch metrics and logs</Typography>
  </Box>
);

export const Settings = () => (
  <Box p={3}>
    <Typography variant="h4">Settings</Typography>
    <Typography>Configure AWS credentials and preferences</Typography>
  </Box>
);
