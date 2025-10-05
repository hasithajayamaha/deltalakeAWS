import { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Database as DatabaseIcon,
  AttachMoney as MoneyIcon,
  CloudQueue as CloudIcon,
} from '@mui/icons-material';
import apiService from '../services/api';

interface DashboardStats {
  totalResources: number;
  s3Buckets: number;
  glueDatabases: number;
  monthlyCost: number;
  lastUpdate: string;
}

const Dashboard = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch discovery data
      const discoveryData = await apiService.discoverResources();
      
      // Fetch cost estimate
      const costData = await apiService.estimateCost({ scenario: 'medium' });

      setStats({
        totalResources: discoveryData.summary?.total_resources || 0,
        s3Buckets: discoveryData.summary?.s3_buckets_count || 0,
        glueDatabases: discoveryData.summary?.glue_databases_count || 0,
        monthlyCost: costData.monthly_cost || 0,
        lastUpdate: discoveryData.timestamp || new Date().toISOString(),
      });
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        DataLake Dashboard
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Total Resources Card */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CloudIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Resources</Typography>
              </Box>
              <Typography variant="h3">{stats?.totalResources || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                AWS Resources
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* S3 Buckets Card */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">S3 Buckets</Typography>
              </Box>
              <Typography variant="h3">{stats?.s3Buckets || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                Storage Buckets
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Glue Databases Card */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <DatabaseIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Glue Databases</Typography>
              </Box>
              <Typography variant="h3">{stats?.glueDatabases || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                Data Catalogs
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Monthly Cost Card */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MoneyIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Monthly Cost</Typography>
              </Box>
              <Typography variant="h3">
                ${stats?.monthlyCost.toFixed(2) || '0.00'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Estimated (Medium)
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Quick Actions
          </Typography>
          <Box display="flex" gap={2} flexWrap="wrap">
            <Button variant="contained" color="primary">
              Discover Resources
            </Button>
            <Button variant="outlined" color="primary">
              View Architecture
            </Button>
            <Button variant="outlined" color="secondary">
              Estimate Costs
            </Button>
            <Button variant="outlined">
              View Logs
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Last Update */}
      <Typography variant="body2" color="text.secondary">
        Last updated: {stats?.lastUpdate ? new Date(stats.lastUpdate).toLocaleString() : 'Never'}
      </Typography>
    </Box>
  );
};

export default Dashboard;
