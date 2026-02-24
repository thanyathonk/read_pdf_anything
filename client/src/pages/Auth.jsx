import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAppContext } from '../context/AppContext';
import { assets } from '../assets/assets';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, register, loginWithGoogle, isAuthenticated, error, clearError } = useAuth();
  const { theme } = useAppContext();
  const navigate = useNavigate();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/chat');
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleResponse = useCallback(async (response) => {
    if (response.credential) {
      setIsSubmitting(true);
      try {
        const result = await loginWithGoogle(response.credential);
        setIsSubmitting(false);
        
        if (result.success) {
          navigate('/chat');
        } else {
          setLocalError(result.error || 'Google login failed');
        }
      } catch (error) {
        console.error('Google login error:', error);
        setIsSubmitting(false);
        setLocalError(error.message || 'Google login failed. Please check your Google OAuth settings.');
      }
    } else if (response.error) {
      console.error('Google Sign-In error:', response.error);
      setLocalError(`Google Sign-In error: ${response.error}. Please check your Google OAuth configuration.`);
    }
  }, [loginWithGoogle, navigate]);

  // Load Google Sign-In script
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      return;
    }

    let retryCount = 0;
    const MAX_RETRIES = 10;

    const initializeGoogleSignIn = () => {
      try {
        if (!window.google?.accounts?.id) {
          if (retryCount < MAX_RETRIES) {
            retryCount++;
            setTimeout(initializeGoogleSignIn, 500);
          }
          return;
        }

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
          ux_mode: 'popup', // Use popup mode
          itp_support: true, // Support Intelligent Tracking Prevention
        });
        
        // Render button
        const renderButton = () => {
          const buttonElement = document.getElementById('google-signin-button');
          if (buttonElement) {
            buttonElement.innerHTML = ''; // Clear first
            try {
              window.google.accounts.id.renderButton(
                buttonElement,
                { 
                  theme: theme === 'dark' ? 'filled_black' : 'outline',
                  size: 'large',
                  width: '100%',
                  text: isLogin ? 'signin_with' : 'signup_with',
                  type: 'standard'
                }
              );
            } catch (error) {
              setLocalError('Failed to load Google Sign-In button');
            }
          } else {
            setTimeout(renderButton, 100);
          }
        };
        
        setTimeout(renderButton, 200);
      } catch (error) {
        setLocalError(`Failed to initialize Google Sign-In: ${error.message}`);
      }
    };

    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript) {
      if (window.google?.accounts?.id) {
        initializeGoogleSignIn();
      } else {
        // Wait for script to finish loading
        const checkGoogle = setInterval(() => {
          if (window.google?.accounts?.id) {
            clearInterval(checkGoogle);
            initializeGoogleSignIn();
          }
        }, 100);
        
        // Timeout after 5 seconds
        setTimeout(() => {
          clearInterval(checkGoogle);
          if (!window.google?.accounts?.id) {
            setLocalError('Google Sign-In failed to load. Please refresh the page.');
          }
        }, 5000);
      }
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    
    script.onload = () => {
      initializeGoogleSignIn();
    };

    script.onerror = () => {
      setLocalError('Failed to load Google Sign-In. Please check your internet connection.');
    };

    document.body.appendChild(script);
  }, [theme, isLogin, handleGoogleResponse]);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    clearError();

    if (!isLogin && password !== confirmPassword) {
      setLocalError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters');
      return;
    }

    setIsSubmitting(true);

    let result;
    if (isLogin) {
      result = await login(email, password);
    } else {
      result = await register(email, name, password);
    }

    setIsSubmitting(false);

    if (result.success) {
      navigate('/chat');
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setLocalError('');
    clearError();
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <img 
            src={theme === 'dark' ? assets.logo_full : assets.logo_full_dark} 
            alt="Logo" 
            className="h-12 mx-auto mb-4"
          />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isLogin ? 'Welcome Back' : 'Create Account'}
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {isLogin 
              ? 'Sign in to save your chat history' 
              : 'Register to unlock all features'}
          </p>
        </div>

        {/* Auth Form */}
        <div className="bg-white/90 dark:bg-slate-800/70 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 dark:border-blue-500/20 p-8">
          {/* Error Message */}
          {(error || localError) && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg">
              <p className="text-sm text-red-600 dark:text-red-400">
                {error || localError}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name field (register only) */}
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={!isLogin}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-blue-500/50 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
                  placeholder="Your name"
                />
              </div>
            )}

            {/* Email field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-blue-500/50 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
                placeholder="your@email.com"
              />
            </div>

            {/* Password field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-blue-500/50 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
                placeholder="••••••••"
              />
            </div>

            {/* Confirm Password (register only) */}
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required={!isLogin}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-blue-500/50 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
                  placeholder="••••••••"
                />
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Please wait...</span>
                </>
              ) : (
                <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center">
            <div className="flex-1 border-t border-gray-300 dark:border-blue-500/30"></div>
            <span className="px-4 text-sm text-gray-500 dark:text-gray-400">or</span>
            <div className="flex-1 border-t border-gray-300 dark:border-blue-500/30"></div>
          </div>

          {/* Google Sign In */}
          {GOOGLE_CLIENT_ID ? (
            // <div>
            //   <div id="google-signin-button" className="flex justify-center min-h-[40px]"></div>
            //   {!document.getElementById('google-signin-button')?.hasChildNodes() && (
            //     <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            //       Loading Google Sign-In...
            //     </p>
            //   )}
            // </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  setIsSubmitting(true);
                  
                  // Get authorization URL from backend (simple login, no Gmail)
                  const { getGoogleAuthUrl } = await import('../services/api');
                  const response = await getGoogleAuthUrl(true); // true = simple login
                  
                  if (response.success && response.authorization_url) {
                    // Redirect to Google OAuth
                    window.location.href = response.authorization_url;
                  } else {
                    setLocalError('Failed to get Google authorization URL');
                    setIsSubmitting(false);
                  }
                } catch (error) {
                  console.error('Google Sign-In error:', error);
                  setLocalError(error.message || 'Failed to start Google Sign-In');
                  setIsSubmitting(false);
                }
              }}
              disabled={isSubmitting}
              className="w-full py-3 px-4 border border-gray-300 dark:border-blue-500/50 rounded-lg flex items-center justify-center gap-3 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  <span>Redirecting...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span>Sign in with Google</span>
                </>
              )}
            </button>
            
          ) : (
            <button
              disabled
              className="w-full py-3 px-4 border border-gray-300 dark:border-blue-500/50 rounded-lg flex items-center justify-center gap-3 text-gray-600 dark:text-gray-400 opacity-50 cursor-not-allowed"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>Google Sign In (Not configured)</span>
            </button>
          )}

          {/* Toggle Login/Register */}
          <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={toggleMode}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
            >
              {isLogin ? 'Register' : 'Sign In'}
            </button>
          </p>

          {/* Continue as Guest */}
          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
            >
              Continue as guest (no history saved)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Auth;

