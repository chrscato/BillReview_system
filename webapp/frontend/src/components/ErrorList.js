import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography,
  Chip,
  Box,
  IconButton,
} from '@mui/material';
import { ErrorOutline, Warning, Info } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

export const ErrorList = ({ errors }) => {
  const navigate = useNavigate();

  const getSeverityIcon = (severity) => {
    switch (severity.toLowerCase()) {
      case 'error':
        return <ErrorOutline color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      default:
        return <Info color="info" />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity.toLowerCase()) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  const handleErrorClick = (error) => {
    navigate(`/error/${error.file_info.file_name}`);
  };

  return (
    <Paper sx={{ mt: 2 }}>
      <List>
        {errors.map((error, index) => (
          <ListItem
            key={`${error.file_info.file_name}-${index}`}
            divider={index < errors.length - 1}
            button
            onClick={() => handleErrorClick(error)}
          >
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  {getSeverityIcon(error.validation_summary.severity_level)}
                  <Typography>
                    {error.failure_details.error_code}: {error.failure_details.error_description}
                  </Typography>
                </Box>
              }
              secondary={
                <Box display="flex" flexDirection="column" gap={1} mt={1}>
                  <Typography variant="body2" color="text.secondary">
                    {error.failure_details.suggestion}
                  </Typography>
                  <Box display="flex" gap={1}>
                    <Chip
                      size="small"
                      label={error.validation_summary.validation_type}
                      color={getSeverityColor(error.validation_summary.severity_level)}
                      variant="outlined"
                    />
                    <Chip
                      size="small"
                      label={`File: ${error.file_info.file_name}`}
                      variant="outlined"
                    />
                  </Box>
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}; 