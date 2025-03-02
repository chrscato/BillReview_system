import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const ValidationDashboard = () => {
  const [sessions, setSessions] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    // Fetch validation sessions
    fetch('/api/sessions')
      .then((res) => res.json())
      .then((data) => setSessions(data));

    // Fetch error statistics
    fetch('/api/stats/common-errors')
      .then((res) => res.json())
      .then((data) => setStatistics(data));
  }, []);

  const handleSessionSelect = (sessionId) => {
    fetch(`/api/sessions/${sessionId}`)
      .then((res) => res.json())
      .then((data) => setSelectedSession(data));
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        {/* Summary Statistics */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Validation Overview
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Total Sessions
                    </Typography>
                    <Typography variant="h5">
                      {sessions.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Total Failures
                    </Typography>
                    <Typography variant="h5">
                      {statistics?.total_failures || 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Success Rate
                    </Typography>
                    <Typography variant="h5">
                      {sessions.length > 0
                        ? Math.round(
                            (sessions.reduce((acc, session) => acc + session.passed_files, 0) /
                              sessions.reduce((acc, session) => acc + session.total_files, 0)) *
                              100
                          ) + '%'
                        : '0%'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Error Distribution Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 300 }}>
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Error Distribution
            </Typography>
            {statistics && (
              <ResponsiveContainer>
                <BarChart data={Object.entries(statistics.error_codes).map(([code, count]) => ({
                  code,
                  count,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="code" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Paper>
        </Grid>

        {/* Recent Sessions */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 300 }}>
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Recent Sessions
            </Typography>
            <List sx={{ overflow: 'auto' }}>
              {sessions.slice(0, 5).map((session) => (
                <ListItem
                  key={session.session_id}
                  button
                  onClick={() => handleSessionSelect(session.session_id)}
                >
                  <ListItemText
                    primary={new Date(session.timestamp).toLocaleString()}
                    secondary={
                      <Box display="flex" gap={1}>
                        <Chip
                          label={`Passed: ${session.passed_files}`}
                          size="small"
                          color="success"
                        />
                        <Chip
                          label={`Failed: ${session.failed_files}`}
                          size="small"
                          color="error"
                        />
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Selected Session Details */}
        {selectedSession && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Session Details
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="subtitle1">
                    Session ID: {selectedSession.session_id}
                  </Typography>
                  <Typography variant="subtitle1">
                    Timestamp: {new Date(selectedSession.timestamp).toLocaleString()}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Common Errors
                  </Typography>
                  {selectedSession.common_errors && (
                    <List>
                      {selectedSession.common_errors.map((error) => (
                        <ListItem key={error.error_code}>
                          <ListItemText
                            primary={`${error.error_code}: ${error.description}`}
                            secondary={`Count: ${error.count}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Container>
  );
};

export default ValidationDashboard; 