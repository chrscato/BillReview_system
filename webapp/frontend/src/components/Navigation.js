import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
} from '@mui/material';
import { Home, Refresh } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

export const Navigation = ({ onRefresh }) => {
  const navigate = useNavigate();

  return (
    <AppBar position="static" color="primary" elevation={1}>
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          <Home />
        </IconButton>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          {process.env.REACT_APP_NAME || 'Bill Review Validation'}
        </Typography>
        <Box>
          <IconButton color="inherit" onClick={onRefresh}>
            <Refresh />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
}; 