import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const ValidationAPI = {
  // Sessions
  getSessions: () => api.get('/sessions'),
  getSessionDetails: (sessionId) => api.get(`/sessions/${sessionId}`),
  getSessionFailures: (sessionId) => api.get(`/sessions/${sessionId}/failures`),

  // Errors and Corrections
  submitCorrection: (failureId, correctionData) =>
    api.post(`/failures/${failureId}/correction`, correctionData),
  getCommonErrors: () => api.get('/stats/common-errors'),
  compareVersions: (fileId) => api.get(`/compare/${fileId}`),
};

// Error handling interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response || error);
    throw error;
  }
); 