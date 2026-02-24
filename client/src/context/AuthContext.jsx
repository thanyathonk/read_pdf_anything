import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { login as loginApi, register as registerApi, googleAuth as googleAuthApi, getCurrentUser, migrateGuestData } from '../services/api';
import { clearAllGuestData, loadGuestData } from '../utils/guestDataManager';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is logged in on mount
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('token');
      if (savedToken) {
        try {
          const userData = await getCurrentUser(savedToken);
          setUser(userData);
          setToken(savedToken);
        } catch (err) {
          // Token is invalid, clear it
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      const response = await loginApi(email, password);
      
      if (response.success && response.data) {
        const { access_token, user: userData } = response.data;
        localStorage.setItem('token', access_token);
        setToken(access_token);
        setUser(userData);
        
        // Migrate guest data if exists
        await migrateGuestDataIfExists(access_token);
        
        return { success: true };
      }
      
      throw new Error(response.message || 'Login failed');
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email, name, password) => {
    try {
      setError(null);
      setLoading(true);
      const response = await registerApi(email, name, password);
      
      if (response.success && response.data) {
        const { access_token, user: userData } = response.data;
        localStorage.setItem('token', access_token);
        setToken(access_token);
        setUser(userData);
        
        // Migrate guest data if exists
        await migrateGuestDataIfExists(access_token);
        
        return { success: true };
      }
      
      throw new Error(response.message || 'Registration failed');
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async (credential) => {
    try {
      setError(null);
      setLoading(true);
      const response = await googleAuthApi(credential);
      
      if (response.success && response.data) {
        const { access_token, user: userData } = response.data;
        localStorage.setItem('token', access_token);
        setToken(access_token);
        setUser(userData);
        
        // Migrate guest data if exists
        await migrateGuestDataIfExists(access_token);
        
        return { success: true };
      }
      
      throw new Error(response.message || 'Google login failed');
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const loginWithGoogleCallback = useCallback(async (data) => {
    try {
      setError(null);
      const { access_token, user: userData } = data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
      // Migrate guest data if exists
      await migrateGuestDataIfExists(access_token);
      
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, []);

  // Helper function to migrate guest data
  const migrateGuestDataIfExists = useCallback(async (token) => {
    try {
      // Get guest PDF IDs from localStorage (with auto-expiry check)
      const guestPdfIds = loadGuestData('guest_pdf_ids') || [];
      
      // Get guest chat messages from localStorage (with auto-expiry check)
      const guestChatMessages = loadGuestData('guest_chat_messages') || [];
      
      // Only migrate if there's data to migrate and it's not expired
      if (guestPdfIds.length > 0 || guestChatMessages.length > 0) {
        await migrateGuestData(token, guestPdfIds, guestChatMessages);
        
        // Clear guest data from localStorage after successful migration
        clearAllGuestData();
        
      }
    } catch (error) {
      console.error('Failed to migrate guest data:', error);
      // Don't throw error - migration failure shouldn't block login
    }
  }, []);

  const logout = useCallback(() => {
    // Clear authentication data
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setError(null);
    
    // Clear all guest data (PDFs, chat history)
    clearAllGuestData();
    
    // Clear user data
    localStorage.removeItem('user_pdf_ids');
    localStorage.removeItem('pdfFiles');
    
    // Reload page to reset all state
    window.location.href = '/';
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = useMemo(() => ({
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user,
    setUser,
    setToken,
    login,
    register,
    loginWithGoogle,
    loginWithGoogleCallback,
    logout,
    clearError,
  }), [user, token, loading, error, setUser, setToken, login, register, loginWithGoogle, loginWithGoogleCallback, logout, clearError]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

