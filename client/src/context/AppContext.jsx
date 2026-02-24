import { createContext, useEffect, useState, useCallback, useMemo, useRef, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { getAllPDFs } from "../services/api";
import { useAuth } from "./AuthContext";
import { loadGuestData, saveGuestData, clearExpiredGuestData } from "../utils/guestDataManager";

const AppContext = createContext();

export const AppContextProvider = ({ children }) => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  const [aiAvatar, setAiAvatar] = useState(localStorage.getItem("aiAvatar") || null);
  const [userAvatar, setUserAvatar] = useState(() => {
    // Load from localStorage first, then use Google avatar if available
    const saved = localStorage.getItem("userAvatar");
    return saved || null;
  });
  // PDF files are now loaded from backend, but we keep localStorage as backup
  // Start with empty array - will be loaded from backend
  const [pdfFiles, setPdfFiles] = useState([]);
  const [selectedPdf, setSelectedPdf] = useState(null);
  const [isLoadingPDFs, setIsLoadingPDFs] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState([]); // Files currently being uploaded
  const hasLoadedPDFsRef = useRef(false);
  
  const togglePdfSelection = useCallback((pdfId) => {
    setPdfFiles(prev => prev.map(pdf => 
      pdf.id === pdfId ? { ...pdf, isSelected: !pdf.isSelected } : pdf
    ));
  }, []);
  
  const toggleAllPdfSelection = useCallback(() => {
    const allSelected = pdfFiles.every(pdf => pdf.isSelected);
    setPdfFiles(prev => prev.map(pdf => ({ ...pdf, isSelected: !allSelected })));
  }, [pdfFiles]);
  
  const getSelectedPdfIds = useCallback(() => {
    return pdfFiles.filter(pdf => pdf.isSelected).map(pdf => pdf.id);
  }, [pdfFiles]);
  
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebarWidth');
    return saved ? parseInt(saved, 10) : 320;
  });
  
  const lastValidWidthRef = useRef(sidebarWidth);
  const isInitializedRef = useRef(false);
  
  useEffect(() => {
    if (!isInitializedRef.current) {
      const saved = localStorage.getItem('sidebarWidth');
      if (saved) {
        const savedWidth = parseInt(saved, 10);
        if (savedWidth >= 240) {
          lastValidWidthRef.current = savedWidth;
          if (sidebarWidth !== savedWidth) {
            setTimeout(() => {
              setSidebarWidth(savedWidth);
            }, 0);
          }
        }
      }
      isInitializedRef.current = true;
    }
  }, [sidebarWidth]);
  
  useEffect(() => {
    if (isInitializedRef.current && sidebarWidth >= 240) {
      lastValidWidthRef.current = sidebarWidth;
      localStorage.setItem('sidebarWidth', sidebarWidth.toString());
    } else if (isInitializedRef.current && sidebarWidth < 240 && lastValidWidthRef.current >= 240) {
      setSidebarWidth(lastValidWidthRef.current);
    }
  }, [sidebarWidth]);

  const stableNavigate = useCallback((...args) => navigate(...args), [navigate]);

  // Load PDFs from backend once on app start
  const loadPDFs = useCallback(async () => {
    // Don't reload if already loaded
    if (hasLoadedPDFsRef.current) {
      return;
    }

    try {
      setIsLoadingPDFs(true);
      
      if (isAuthenticated) {
        // Logged-in users: Load from backend (MongoDB)
        const allPDFs = await getAllPDFs();
        
        // Map backend PDFs to frontend format
        const mappedPDFs = allPDFs.map(pdf => ({
          id: pdf.id,
          name: pdf.filename,
          size: pdf.size,
          chunkCount: pdf.chunkCount,
          uploadedAt: pdf.uploadedAt,
          isSelected: true, // Default to selected
        }));
        
        setPdfFiles(mappedPDFs);
      } else {
        // Guest users: Load from localStorage with auto-expiry (1 day)
        // Clear expired data first
        clearExpiredGuestData();
        
        const savedPDFs = loadGuestData('guest_pdf_files');
        if (savedPDFs && Array.isArray(savedPDFs)) {
          setPdfFiles(savedPDFs.map(pdf => ({
            ...pdf,
            isSelected: pdf.isSelected !== undefined ? pdf.isSelected : true
          })));
        } else {
          setPdfFiles([]);
        }
      }
      
      hasLoadedPDFsRef.current = true;
    } catch (error) {
      console.error('Failed to load PDFs:', error);
      // Fallback to localStorage for guest users
      if (!isAuthenticated) {
        const savedPDFs = loadGuestData('guest_pdf_files');
        if (savedPDFs && Array.isArray(savedPDFs)) {
          setPdfFiles(savedPDFs.map(pdf => ({
            ...pdf,
            isSelected: pdf.isSelected !== undefined ? pdf.isSelected : true
          })));
        } else {
          setPdfFiles([]);
        }
      } else {
        setPdfFiles([]);
      }
      hasLoadedPDFsRef.current = true;
    } finally {
      setIsLoadingPDFs(false);
    }
  }, [isAuthenticated]);

  // Refresh PDFs from backend (used after upload/delete)
  const refreshPDFs = useCallback(async () => {
    try {
      setIsLoadingPDFs(true);
      
      if (isAuthenticated) {
        // Logged-in users: Load from backend
        const allPDFs = await getAllPDFs();
        
        // Map backend PDFs to frontend format
        const mappedPDFs = allPDFs.map(pdf => ({
          id: pdf.id,
          name: pdf.filename,
          size: pdf.size,
          chunkCount: pdf.chunkCount,
          uploadedAt: pdf.uploadedAt,
          isSelected: true, // Default to selected
        }));
        
        setPdfFiles(mappedPDFs);
      } else {
        // Guest users: Reload from localStorage with auto-expiry
        clearExpiredGuestData();
        
        const savedPDFs = loadGuestData('guest_pdf_files');
        if (savedPDFs && Array.isArray(savedPDFs)) {
          const validPDFs = savedPDFs;
          
          // Merge with existing state to preserve any newly uploaded PDFs
          setPdfFiles(prev => {
            const existingIds = new Set(prev.map(p => p.id));
            const newPDFs = validPDFs.filter(pdf => !existingIds.has(pdf.id));
            return [...prev, ...newPDFs].map(pdf => ({
              ...pdf,
              isSelected: pdf.isSelected !== undefined ? pdf.isSelected : true
            }));
          });
        } else {
          setPdfFiles([]);
        }
        // If no saved PDFs, keep current state (might be uploading)
      }
    } catch (error) {
      console.error('Failed to refresh PDFs:', error);
      // Don't clear PDFs on error - keep current state
    } finally {
      setIsLoadingPDFs(false);
    }
  }, [isAuthenticated]);

  // Load PDFs once on mount
  useEffect(() => {
    loadPDFs();
  }, [loadPDFs]);

  // Reload PDFs when authentication status changes
  useEffect(() => {
    // Reset the loaded flag when authentication status changes
    // This ensures PDFs are reloaded when user logs in/out
    hasLoadedPDFsRef.current = false;
    loadPDFs();
  }, [isAuthenticated, loadPDFs]);

  useEffect(() => {
    // Save PDF data based on authentication status
    if (pdfFiles.length > 0) {
      if (!isAuthenticated) {
        // Guest mode: Save full PDF metadata to localStorage with timestamp
        // Data will expire after 1 day
        saveGuestData('guest_pdf_files', pdfFiles);
        
        // Also save PDF IDs for migration
        const pdfIds = pdfFiles.map(pdf => pdf.id);
        saveGuestData('guest_pdf_ids', pdfIds);
      } else {
        // Logged-in users: Only save PDF IDs for migration (metadata is in MongoDB)
        const pdfIds = pdfFiles.map(pdf => pdf.id);
        localStorage.setItem('user_pdf_ids', JSON.stringify(pdfIds));
        
        // Clean up guest data if user logged in
        localStorage.removeItem('guest_pdf_files');
        localStorage.removeItem('guest_pdf_ids');
      }
    } else {
      // Clean up if no PDFs
      if (!isAuthenticated) {
        localStorage.removeItem('guest_pdf_files');
        localStorage.removeItem('guest_pdf_ids');
      } else {
        // Clear user PDF IDs when logged out
        localStorage.removeItem('user_pdf_ids');
      }
    }
  }, [pdfFiles, isAuthenticated]);

  // Clear PDF state when logging out
  useEffect(() => {
    if (!isAuthenticated) {
      // Clear PDF files state when user logs out
      setPdfFiles([]);
      // Reset loaded flag to allow reloading when user logs in again
      hasLoadedPDFsRef.current = false;
    }
  }, [isAuthenticated, setPdfFiles]);

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Save AI avatar to localStorage
  useEffect(() => {
    if (aiAvatar) {
      localStorage.setItem("aiAvatar", aiAvatar);
    }
  }, [aiAvatar]);

  // Update user avatar when user logs in (if Google avatar exists and no custom avatar)
  useEffect(() => {
    if (user?.avatar && !localStorage.getItem("userAvatar")) {
      setUserAvatar(user.avatar);
      localStorage.setItem("userAvatar", user.avatar);
    }
  }, [user, setUserAvatar]);

  // Save user avatar to localStorage
  useEffect(() => {
    if (userAvatar) {
      localStorage.setItem("userAvatar", userAvatar);
    }
  }, [userAvatar]);

  const stableSetSidebarWidth = useCallback((newWidth) => {
    if (typeof newWidth === 'function') {
      setSidebarWidth((prevWidth) => {
        const calculated = newWidth(prevWidth);
        const finalWidth = calculated >= 240 ? calculated : prevWidth;
        lastValidWidthRef.current = finalWidth;
        localStorage.setItem('sidebarWidth', finalWidth.toString());
        return finalWidth;
      });
    } else {
      if (newWidth >= 240) {
        lastValidWidthRef.current = newWidth;
        localStorage.setItem('sidebarWidth', newWidth.toString());
        setSidebarWidth(newWidth);
      }
    }
  }, []);
  
  const sidebarWidthValue = sidebarWidth >= 240 ? sidebarWidth : 320;
  
  const value = useMemo(() => ({
    navigate: stableNavigate,
    theme,
    setTheme,
    aiAvatar,
    setAiAvatar,
    userAvatar,
    setUserAvatar,
    sidebarWidth: sidebarWidthValue,
    setSidebarWidth: stableSetSidebarWidth,
    pdfFiles,
    setPdfFiles,
    selectedPdf,
    setSelectedPdf,
    togglePdfSelection,
    toggleAllPdfSelection,
    getSelectedPdfIds,
    isLoadingPDFs,
    refreshPDFs,
    uploadingFiles,
    setUploadingFiles,
  }), [stableNavigate, theme, aiAvatar, userAvatar, sidebarWidthValue, stableSetSidebarWidth, pdfFiles, selectedPdf, togglePdfSelection, toggleAllPdfSelection, getSelectedPdfIds, isLoadingPDFs, refreshPDFs, uploadingFiles]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useAppContext = () => useContext(AppContext);

