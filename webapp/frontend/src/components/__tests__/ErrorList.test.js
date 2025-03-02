import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorList } from '../ErrorList';
import { BrowserRouter } from 'react-router-dom';

// Mock data
const mockErrors = [
  {
    file_info: {
      file_name: 'test-file-1',
      order_id: 'ORDER-001',
    },
    validation_summary: {
      severity_level: 'ERROR',
      validation_type: 'modifier_check',
    },
    failure_details: {
      error_code: 'MOD_001',
      error_description: 'Invalid modifier combination',
      suggestion: 'Review modifier usage',
    },
  },
];

// Wrap component with router for testing
const renderWithRouter = (ui) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('ErrorList Component', () => {
  test('renders error items correctly', () => {
    renderWithRouter(<ErrorList errors={mockErrors} />);
    
    // Check if error code and description are displayed
    expect(screen.getByText(/MOD_001/)).toBeInTheDocument();
    expect(screen.getByText(/Invalid modifier combination/)).toBeInTheDocument();
    
    // Check if suggestion is displayed
    expect(screen.getByText(/Review modifier usage/)).toBeInTheDocument();
    
    // Check if validation type chip is displayed
    expect(screen.getByText(/modifier_check/)).toBeInTheDocument();
  });

  test('navigates on error click', () => {
    const { container } = renderWithRouter(<ErrorList errors={mockErrors} />);
    
    // Find and click the error item
    const errorItem = container.querySelector('[role="button"]');
    fireEvent.click(errorItem);
    
    // Check if we're on the correct path
    expect(window.location.pathname).toBe('/error/test-file-1');
  });

  test('displays correct severity indicators', () => {
    renderWithRouter(<ErrorList errors={mockErrors} />);
    
    // Check if error icon is present
    const errorIcon = container.querySelector('[class*="MuiSvgIcon-colorError"]');
    expect(errorIcon).toBeInTheDocument();
  });
}); 