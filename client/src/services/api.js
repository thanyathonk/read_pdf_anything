const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ==================== AUTH API ====================

/**
 * Register a new user
 * @param {string} email - User email
 * @param {string} name - User name
 * @param {string} password - User password
 * @returns {Promise<Object>} Auth response with token and user
 */
export const register = async (email, name, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, name, password }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }

    return data;
  } catch (error) {
    console.error('Register error:', error);
    throw error;
  }
};

/**
 * Login with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Auth response with token and user
 */
export const login = async (email, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    return data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

/**
 * Login with Google (Simple - ID Token only)
 * @param {string} credential - Google ID token
 * @returns {Promise<Object>} Auth response with token and user
 */
export const googleAuth = async (credential) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ credential }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Google authentication failed');
    }

    return data;
  } catch (error) {
    console.error('Google auth error:', error);
    throw error;
  }
};

/**
 * Get Google OAuth authorization URL
 * @param {boolean} simple - Use simple login (no Gmail access)
 * @returns {Promise<Object>} Authorization URL
 */
export const getGoogleAuthUrl = async (simple = true) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/google/authorize?simple=${simple}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to get authorization URL');
    }

    return data;
  } catch (error) {
    console.error('Get Google auth URL error:', error);
    throw error;
  }
};

/**
 * Migrate guest data (PDFs and chat messages) to user account
 * @param {string} token - JWT token
 * @param {Array<string>} pdfIds - Array of PDF IDs
 * @param {Array<Object>} chatMessages - Array of chat messages
 * @returns {Promise<Object>} Migration response
 */
export const migrateGuestData = async (token, pdfIds = [], chatMessages = []) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/migrate-guest-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        pdf_ids: pdfIds,
        chat_messages: chatMessages
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to migrate guest data');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Migrate guest data error:', error);
    throw error;
  }
};

/**
 * Handle Google OAuth callback (with Gmail access)
 * @param {string} code - Authorization code
 * @returns {Promise<Object>} Auth response with token, user, and emails
 */
export const googleAuthCallback = async (code) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/google/callback?code=${code}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Google authentication failed');
    }

    return data;
  } catch (error) {
    console.error('Google auth callback error:', error);
    throw error;
  }
};

/**
 * Fetch emails from Gmail
 * @param {string} token - JWT token
 * @param {number} maxResults - Maximum number of emails to fetch
 * @returns {Promise<Object>} Emails data
 */
export const fetchEmails = async (token, maxResults = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/gmail/emails?max_results=${maxResults}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch emails');
    }

    return data;
  } catch (error) {
    console.error('Fetch emails error:', error);
    throw error;
  }
};

/**
 * Get current user info
 * @param {string} token - JWT token
 * @returns {Promise<Object>} User info
 */
export const getCurrentUser = async (token) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    return await response.json();
  } catch (error) {
    console.error('Get current user error:', error);
    throw error;
  }
};

/**
 * Check auth service status
 * @returns {Promise<Object>} Auth status
 */
export const getAuthStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/status`);
    return await response.json();
  } catch (error) {
    console.error('Auth status error:', error);
    return { database_connected: false, google_oauth_enabled: false };
  }
};

// ==================== PDF API ====================

/**
 * Upload PDF file to backend
 * @param {File} file - PDF file to upload
 * @returns {Promise<Object>} PDF data with id, filename, size, chunkCount
 */
export const uploadPDF = async (file) => {
  try {
    // Validate file size before uploading (10MB limit)
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    if (file.size > MAX_FILE_SIZE) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      throw new Error(`File size (${fileSizeMB}MB) exceeds maximum limit of 10MB. Please upload a smaller file.`);
    }

    const token = localStorage.getItem('token');
    const headers = {};
    
    // Add authorization header if user is logged in
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/pdf/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload PDF');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Upload PDF error:', error);
    throw error;
  }
};

/**
 * Get all uploaded PDFs
 * @returns {Promise<Array>} Array of PDF info
 */
export const getAllPDFs = async () => {
  try {
    const token = localStorage.getItem('token');
    const headers = {};
    
    // Add authorization header if user is logged in
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/pdf/all`, {
      headers,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get PDFs');
    }

    const data = await response.json();
    return data.pdfs || [];
  } catch (error) {
    console.error('Get all PDFs error:', error);
    throw error;
  }
};

/**
 * Get PDF info by ID
 * @param {string} pdfId - PDF ID
 * @returns {Promise<Object>} PDF info
 */
export const getPDFInfo = async (pdfId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pdf/${pdfId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get PDF info');
    }

    const data = await response.json();
    return data.pdf;
  } catch (error) {
    console.error('Get PDF info error:', error);
    throw error;
  }
};

/**
 * Update PDF filename
 * @param {string} pdfId - PDF ID
 * @param {string} newFilename - New filename
 * @returns {Promise<Object>} Success response
 */
export const updatePDFName = async (pdfId, newFilename) => {
  try {
    const token = localStorage.getItem('token');
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/pdf/${pdfId}/name`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ filename: newFilename }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update PDF name');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Update PDF name error:', error);
    throw error;
  }
};

/**
 * Delete PDF by ID
 * @param {string} pdfId - PDF ID
 * @returns {Promise<Object>} Success response
 */
export const deletePDF = async (pdfId) => {
  try {
    const token = localStorage.getItem('token');
    const headers = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/pdf/${pdfId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete PDF');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Delete PDF error:', error);
    throw error;
  }
};

/**
 * Chat with PDF using RAG
 * @param {string} message - User message
 * @param {Array<string>} pdfIds - Array of selected PDF IDs
 * @param {AbortSignal} signal - Optional AbortSignal for cancellation
 * @param {Array<Object>} chatHistory - Optional chat history
 * @returns {Promise<Object>} Response with answer and sources
 */
export const chatWithPDF = async (message, pdfIds, signal = null, chatHistory = []) => {
  try {
    const token = localStorage.getItem('token');
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // Add authorization header if user is logged in
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/chat/pdf`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        pdfIds,
        chatHistory: chatHistory.length > 0 ? chatHistory.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp ? String(msg.timestamp) : undefined
        })).filter(msg => msg.content) : undefined
      }),
      signal, // Pass AbortSignal for cancellation
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to chat with PDF');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    // Don't log abort errors as they are intentional
    if (error.name === 'AbortError') {
      throw new Error('Request cancelled');
    }
    console.error('Chat with PDF error:', error);
    throw error;
  }
};

/**
 * Get chat history for authenticated user
 * @param {string} token - JWT token
 * @returns {Promise<Object>} Chat history
 */
export const getChatHistory = async (token) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/chat/history`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get chat history');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Get chat history error:', error);
    throw error;
  }
};

/**
 * Save chat history for authenticated user
 * @param {string} token - JWT token
 * @param {Array<Object>} messages - Chat messages
 * @returns {Promise<Object>} Success response
 */
export const saveChatHistory = async (token, messages) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/chat/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(messages)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save chat history');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Save chat history error:', error);
    throw error;
  }
};

