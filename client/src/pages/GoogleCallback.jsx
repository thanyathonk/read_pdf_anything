import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { googleAuthCallback } from '../services/api';

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithGoogleCallback } = useAuth();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const error = searchParams.get('error');
      const state = searchParams.get('state');

      if (error) {
        setError('Authentication cancelled or failed');
        setLoading(false);
        setTimeout(() => navigate('/auth'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        setLoading(false);
        setTimeout(() => navigate('/auth'), 3000);
        return;
      }

      try {
        // Check if this is a simple login (no Gmail)
        const isSimpleLogin = state && state.includes('simple=true');
        
        if (isSimpleLogin) {
          // Handle simple login
          const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
          const response = await fetch(`${API_BASE_URL}/api/auth/google/simple-callback?code=${code}&state=${state || ''}`);
          const data = await response.json();
          
          if (response.ok && data.success && data.data) {
            const { access_token, user: userData } = data.data;
            
            // Store token
            localStorage.setItem('token', access_token);
            
            // Update auth context
            if (loginWithGoogleCallback) {
              await loginWithGoogleCallback(data.data);
            }
            
            // Navigate to chat
            navigate('/chat');
          } else {
            setError(data.detail || 'Authentication failed');
            setTimeout(() => navigate('/auth'), 3000);
          }
        } else {
          // Handle full OAuth with Gmail
          const response = await googleAuthCallback(code);
          
          if (response.success && response.data) {
            const { access_token, user: userData, emails } = response.data;
            
            // Store token and user
            localStorage.setItem('token', access_token);
            
            // Store emails if available
            if (emails && emails.length > 0) {
              localStorage.setItem('gmail_emails', JSON.stringify(emails));
            }
            
            // Update auth context
            if (loginWithGoogleCallback) {
              await loginWithGoogleCallback(response.data);
            }
            
            // Navigate to chat
            navigate('/chat');
          } else {
            setError('Authentication failed');
            setTimeout(() => navigate('/auth'), 3000);
          }
        }
      } catch (err) {
        console.error('Callback error:', err);
        setError(err.message || 'Authentication failed');
        setTimeout(() => navigate('/auth'), 3000);
      } finally {
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate, loginWithGoogleCallback]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        {loading ? (
          <>
                  <div className="w-16 h-16 border-4 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Completing authentication...</p>
          </>
        ) : error ? (
          <>
            <div className="text-red-500 text-xl mb-4">⚠️</div>
            <p className="text-red-600 dark:text-red-400 mb-2">{error}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Redirecting to login page...</p>
          </>
        ) : null}
      </div>
    </div>
  );
};

export default GoogleCallback;

