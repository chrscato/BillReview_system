import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { CorrectionForm } from './CorrectionForm';

export const ErrorDetails = ({ error }) => {
  const [openCorrection, setOpenCorrection] = useState(false);

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

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Grid container spacing={2}>
        {/* Header */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6" component="h3">
              Validation Error
            </Typography>
            <Chip
              label={error.validation_summary.severity_level}
              color={getSeverityColor(error.validation_summary.severity_level)}
            />
          </Box>
        </Grid>

        {/* Error Details */}
        <Grid item xs={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Error Information</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Error Code</Typography>
                  <Typography>{error.failure_details.error_code}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Validation Type</Typography>
                  <Typography>{error.validation_summary.validation_type}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Description</Typography>
                  <Typography>{error.failure_details.error_description}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Suggestion</Typography>
                  <Typography>{error.failure_details.suggestion}</Typography>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Value Comparison */}
        <Grid item xs={12}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Value Comparison</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Expected Value</Typography>
                  <Typography>
                    {JSON.stringify(error.failure_details.expected_value, null, 2)}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Actual Value</Typography>
                  <Typography>
                    {JSON.stringify(error.failure_details.actual_value, null, 2)}
                  </Typography>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Context Information */}
        <Grid item xs={12}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Context Information</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">HCFA Data</Typography>
                  <pre>
                    {JSON.stringify(error.context.hcfa_data, null, 2)}
                  </pre>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Reference Data</Typography>
                  <pre>
                    {JSON.stringify(error.context.reference_data, null, 2)}
                  </pre>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Actions */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="flex-end" gap={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => setOpenCorrection(true)}
            >
              Submit Correction
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Correction Dialog */}
      <Dialog
        open={openCorrection}
        onClose={() => setOpenCorrection(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Submit Correction</DialogTitle>
        <DialogContent>
          <CorrectionForm
            error={error}
            onSubmit={() => setOpenCorrection(false)}
          />
        </DialogContent>
      </Dialog>
    </Paper>
  );
}; 