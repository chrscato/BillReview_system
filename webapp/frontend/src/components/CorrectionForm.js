import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Grid,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';

export const CorrectionForm = ({ error, onSubmit }) => {
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);

  const handleChange = (field) => (event) => {
    setFormData((prev) => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSubmitStatus(null);

    try {
      const response = await fetch(
        `/api/failures/${error.file_info.file_name}/correction`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            correction_data: formData,
            error_code: error.failure_details.error_code,
            validation_type: error.validation_summary.validation_type,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to submit correction');
      }

      setSubmitStatus({
        type: 'success',
        message: 'Correction submitted successfully',
      });
      onSubmit();
    } catch (error) {
      setSubmitStatus({
        type: 'error',
        message: 'Failed to submit correction: ' + error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Generate form fields based on error type
  const getFormFields = () => {
    const fields = [];
    const errorType = error.validation_summary.validation_type.toLowerCase();

    if (errorType.includes('modifier')) {
      fields.push({
        name: 'modifier',
        label: 'Corrected Modifier',
        defaultValue: error.context.hcfa_data.modifier,
      });
    }

    if (errorType.includes('unit')) {
      fields.push({
        name: 'units',
        label: 'Corrected Units',
        type: 'number',
        defaultValue: error.context.hcfa_data.units,
      });
    }

    if (errorType.includes('rate')) {
      fields.push({
        name: 'rate',
        label: 'Corrected Rate',
        type: 'number',
        defaultValue: error.context.hcfa_data.rate,
      });
    }

    // Add a notes field for all corrections
    fields.push({
      name: 'notes',
      label: 'Correction Notes',
      multiline: true,
      rows: 4,
    });

    return fields;
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Grid container spacing={3}>
        {/* Error Summary */}
        <Grid item xs={12}>
          <Typography variant="subtitle1" gutterBottom>
            Error Code: {error.failure_details.error_code}
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {error.failure_details.error_description}
          </Typography>
        </Grid>

        {/* Form Fields */}
        {getFormFields().map((field) => (
          <Grid item xs={12} key={field.name}>
            <TextField
              fullWidth
              id={field.name}
              name={field.name}
              label={field.label}
              type={field.type || 'text'}
              multiline={field.multiline}
              rows={field.rows}
              defaultValue={field.defaultValue}
              onChange={handleChange(field.name)}
              required={!field.optional}
            />
          </Grid>
        ))}

        {/* Status Message */}
        {submitStatus && (
          <Grid item xs={12}>
            <Alert severity={submitStatus.type}>{submitStatus.message}</Alert>
          </Grid>
        )}

        {/* Submit Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="flex-end" gap={2}>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={loading}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Submit Correction'
              )}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}; 