import React, { useState, useRef, useEffect } from "react";
import { useAppContext } from "../context/AppContext";
import { useAuth } from "../context/AuthContext";
import { assets } from "../assets/assets";
import { useNavigate } from "react-router-dom";
import Toast from "./Toast";
import { uploadPDF, deletePDF as deletePDFAPI, updatePDFName } from "../services/api";
import { saveGuestData, loadGuestData } from "../utils/guestDataManager";

const Sidebar = ({ isTabMode = false }) =>  {

  const { sidebarWidth, setSidebarWidth, pdfFiles, setPdfFiles, togglePdfSelection, toggleAllPdfSelection, isLoadingPDFs, refreshPDFs, uploadingFiles, setUploadingFiles } = useAppContext();
  const { isAuthenticated } = useAuth();
  const [search, setSearch] = useState("");
  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [toast, setToast] = useState(null);
  const [editingPdfId, setEditingPdfId] = useState(null);
  const [editingName, setEditingName] = useState("");
  const sidebarRef = useRef(null);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);
  const hasMoved = useRef(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Disable resize functionality in tab mode
    if (isTabMode) {
      return;
    }

    const handleMouseMove = (e) => {
      if (!isResizing) return;
      
      const deltaX = Math.abs(e.clientX - resizeStartX.current);
      if (deltaX < 3) {
        hasMoved.current = false;
        return;
      }
      
      hasMoved.current = true;
      
      const newWidth = resizeStartWidth.current + (e.clientX - resizeStartX.current);
      const minWidth = 240;
      const maxWidth = window.innerWidth * 0.6;
      
      const clampedWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
      if (clampedWidth >= minWidth && clampedWidth <= maxWidth) {
        setSidebarWidth(clampedWidth);
      }
    };

    const handleMouseUp = () => {
      if (!hasMoved.current) {
        setIsResizing(false);
      } else {
        setIsResizing(false);
      }
      hasMoved.current = false;
      resizeStartX.current = 0;
      resizeStartWidth.current = 0;
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, setSidebarWidth, isTabMode]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    
    const MAX_FILES = 10;
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes
    const currentCount = pdfFiles.length;
    const remainingSlots = MAX_FILES - currentCount;
    
    if (remainingSlots <= 0) {
      showToast(`Maximum ${MAX_FILES} PDF files allowed. Please delete some files before uploading new ones.`, 'warning');
      return;
    }
    
    const allFiles = Array.from(files);
    
    // Filter by file type and size
    const pdfFilesOnly = allFiles.filter(file => {
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      const isValidSize = file.size <= MAX_FILE_SIZE;
      return isPdf && isValidSize;
    });
    
    const nonPdfFiles = allFiles.filter(file => {
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      return !isPdf;
    });
    
    const oversizedFiles = allFiles.filter(file => {
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      return isPdf && file.size > MAX_FILE_SIZE;
    });
    
    if (nonPdfFiles.length > 0) {
      showToast(`Only PDF files are allowed. ${nonPdfFiles.length} non-PDF file(s) were ignored.`, 'error');
    }
    
    if (oversizedFiles.length > 0) {
      const maxSizeMB = (MAX_FILE_SIZE / (1024 * 1024)).toFixed(0);
      showToast(`${oversizedFiles.length} file(s) exceed the maximum size of ${maxSizeMB}MB and were ignored.`, 'error');
    }
    
    if (pdfFilesOnly.length === 0) {
      if (nonPdfFiles.length === 0 && oversizedFiles.length === 0) {
        showToast('No valid PDF files found. Please upload PDF files only.', 'error');
      }
      return;
    }
    
    let filesToAdd = pdfFilesOnly;
    let warningMessage = '';
    
    if (filesToAdd.length > remainingSlots) {
      filesToAdd = filesToAdd.slice(0, remainingSlots);
      warningMessage = `Maximum ${MAX_FILES} PDF files allowed. Only the first ${remainingSlots} file(s) were uploaded.`;
    }
    
    // Add files to uploading state with temporary IDs
    const tempUploadingFiles = filesToAdd.map((file, index) => ({
      tempId: `uploading-${Date.now()}-${index}`,
      name: file.name,
      size: file.size,
      isUploading: true,
      progress: 0,
    }));
    
    setUploadingFiles(tempUploadingFiles);
    navigate('/chat');
    
    // Upload files to backend one by one
    const successfulUploads = [];
    
    for (let i = 0; i < filesToAdd.length; i++) {
      const file = filesToAdd[i];
      const tempFile = tempUploadingFiles[i];
      
      try {
        // Update progress for current file
        setUploadingFiles(prev =>
          prev.map(f =>
            f.tempId === tempFile.tempId
              ? { ...f, progress: 50, status: 'Processing...' }
              : f
          )
        );
        const result = await uploadPDF(file);
        
        const newPDF = {
          id: result.pdfId,
          name: result.filename,
          size: result.size,
          chunkCount: result.chunkCount,
          uploadedAt: Date.now(),
          isSelected: true,
        };
        
        successfulUploads.push(newPDF);
        
        // For guest users: Save metadata to localStorage immediately using guestDataManager
        // This prevents server from storing guest metadata
        if (!isAuthenticated && result.pdfId) {
          const savedPDFs = loadGuestData('guest_pdf_files') || [];
          // Check if PDF already exists (avoid duplicates)
          const exists = savedPDFs.some(pdf => pdf.id === result.pdfId);
          if (!exists) {
            savedPDFs.push(newPDF);
            saveGuestData('guest_pdf_files', savedPDFs);
            setPdfFiles(prev => {
              const updated = [...prev, newPDF];
              return updated;
            });
          }
        }
        
        // Update progress to 100% before removing
        setUploadingFiles(prev => prev.map(f => 
          f.tempId === tempFile.tempId 
            ? { ...f, progress: 100, status: 'Completed' } 
            : f
        ));
        
        // Remove this file from uploading state after a short delay
        setTimeout(() => {
          setUploadingFiles(prev => prev.filter(f => f.tempId !== tempFile.tempId));
        }, 500);
        
      } catch (error) {
        
        // Mark file as failed
        setUploadingFiles(prev => prev.map(f => 
          f.tempId === tempFile.tempId 
            ? { ...f, isUploading: false, error: error.message } 
            : f
        ));
        
        showToast(`Failed to upload ${file.name}: ${error.message}`, 'error');
        
        // Remove failed file after 3 seconds
        setTimeout(() => {
          setUploadingFiles(prev => prev.filter(f => f.tempId !== tempFile.tempId));
        }, 3000);
      }
    }
    
    // Show success/warning/error messages
    if (successfulUploads.length > 0) {
      // Refresh PDFs from backend only for authenticated users
      // For guest users, PDFs are already added to state and localStorage
      if (isAuthenticated) {
        await refreshPDFs();
      }
      
      if (warningMessage) {
        showToast(warningMessage, 'warning');
      } else {
        showToast(`${successfulUploads.length} PDF file(s) uploaded and processed successfully.`, 'success');
      }
    } else if (filesToAdd.length > 0) {
      showToast('Failed to upload any PDF files. Please try again.', 'error');
    }
  };

  const handleDeletePdf = async (pdfId) => {
    try {
      // Immediately update UI by removing from state
      setPdfFiles(prev => prev.filter(pdf => pdf.id !== pdfId));
      
      // For guest users: Remove from localStorage using guestDataManager
      if (!isAuthenticated) {
        const savedPDFs = loadGuestData('guest_pdf_files') || [];
        const filteredPDFs = savedPDFs.filter(pdf => pdf.id !== pdfId);
        saveGuestData('guest_pdf_files', filteredPDFs);
      }
      
      // Call backend to delete (don't await to make UI feel faster)
      deletePDFAPI(pdfId).catch(() => {});
      
      showToast('PDF deleted successfully', 'success');
    } catch (error) {
      console.error('Delete PDF error:', error);
      showToast(`Failed to delete PDF: ${error.message}`, 'error');
    }
  };

  const handleStartEdit = (pdfId, currentName) => {
    setEditingPdfId(pdfId);
    setEditingName(currentName);
  };

  const handleCancelEdit = () => {
    setEditingPdfId(null);
    setEditingName("");
  };

  const handleSaveEdit = async (pdfId) => {
    try {
      // Only allow authenticated users
      if (!isAuthenticated) {
        showToast('Please login to edit PDF names', 'error');
        handleCancelEdit();
        return;
      }

      const trimmedName = editingName.trim();
      if (!trimmedName) {
        showToast('PDF name cannot be empty', 'error');
        return;
      }

      // Optimistic UI update
      setPdfFiles(prev => prev.map(pdf => 
        pdf.id === pdfId ? { ...pdf, name: trimmedName } : pdf
      ));

      // Call backend to update
      await updatePDFName(pdfId, trimmedName);
      
      setEditingPdfId(null);
      setEditingName("");
      showToast('PDF name updated successfully', 'success');
    } catch (error) {
      console.error('Update PDF name error:', error);
      showToast(`Failed to update PDF name: ${error.message}`, 'error');
      // Revert optimistic update
      await refreshPDFs();
    }
  };

  return (
    <div 
      ref={sidebarRef}
      onMouseDown={(e) => {
        const rect = sidebarRef.current?.getBoundingClientRect();
        if (rect && e.clientX < rect.right - 6) {
          e.stopPropagation();
        }
      }}
      className={`relative flex flex-col h-full p-5 bg-white/90 dark:bg-gradient-to-b from-slate-950/95 to-slate-900/95 backdrop-blur-3xl border border-gray-200 dark:border-blue-500/30 rounded-xl shadow-lg`}
      style={isTabMode ? {
        width: '100%',
        flexShrink: 0,
        flexGrow: 0,
      } : {
        width: `${sidebarWidth}px`, 
        minWidth: '240px', 
        maxWidth: '60vw',
        flexShrink: 0,
        flexGrow: 0,
        transition: 'none'
      }}
    >
      {/* Resize handle - only show in desktop mode */}
      {!isTabMode && (
        <div
          onMouseDown={(e) => {
            const target = e.target;
            if (target.closest('button, a, [role="button"], input, select, textarea')) {
              return;
            }
            
            const rect = sidebarRef.current?.getBoundingClientRect();
            if (!rect || e.clientX < rect.right - 6) {
              e.stopPropagation();
              return;
            }
            
            if (!e.currentTarget.contains(target) && target !== e.currentTarget) {
              return;
            }
            
            e.preventDefault();
            e.stopPropagation();
            resizeStartX.current = e.clientX;
            resizeStartWidth.current = sidebarWidth;
            hasMoved.current = false;
            setIsResizing(true);
          }}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          onMouseUp={(e) => {
            if (!hasMoved.current) {
              e.preventDefault();
              e.stopPropagation();
              setIsResizing(false);
            }
          }}
          className="hidden md:block absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-blue-500/30 transition-colors group z-10"
          style={{ pointerEvents: 'auto', touchAction: 'none' }}
        >
          <div className="absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/2 w-1 h-20 bg-blue-500/40 rounded-full group-hover:bg-blue-500/80 transition-colors pointer-events-none" />
        </div>
      )}
      {/* Logo */}
      {/* <img
        src={theme === "dark" ? assets.logo_full : assets.logo_full_dark}
        alt=""
        className="w-full max-w-48 cursor-pointer"
      /> */}

      {/* PDF Upload Section */}
      <div
        onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);
            
            const files = Array.from(e.dataTransfer.files);
            handleFileUpload(files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center w-full py-8 mt-10 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
            isDragging 
              ? 'border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-500/20' 
              : 'border-gray-300 dark:border-blue-500/30 hover:border-blue-600/50 dark:hover:border-blue-400/50'
          }`}
        >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files);
            handleFileUpload(files);
            e.target.value = '';
          }}
        />
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-400 dark:to-blue-500 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isDragging ? 'Drop PDF files here' : 'Drag & Drop PDF files'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">PDF files only • or click to browse</p>
        </div>
      </div>

      <div className="flex items-center gap-2 p-3 mt-4 border border-gray-400 dark:border-white/20 rounded-md">
        <img src={assets.search_icon} className="w-4 not-dark:invert" alt="" />
        <input
          onChange={(e) => setSearch(e.target.value)}
          value={search}
          type="text"
          placeholder="Search PDF files"
          className="text-xs placeholder:text-gray-400 outline-none bg-transparent flex-1"
        />
      </div>

      {pdfFiles.length > 0 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Uploaded PDFs</p>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleAllPdfSelection();
              }}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
            >
              {pdfFiles.every(f => f.isSelected) ? 'Deselect All' : 'Select All'}
            </button>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {pdfFiles.filter(f => f.isSelected).length} selected
            </p>
          </div>
        </div>
      )}
      <div className="flex-1 overflow-y-scroll mt-3 text-sm space-y-2">
        {/* Always show uploading files if any */}
        {uploadingFiles.length > 0 && (
          <>
            {uploadingFiles.map((file) => (
              <div
                key={file.tempId}
                className="relative p-3 rounded-md flex items-center gap-3 overflow-hidden"
                style={{
                  background: 'linear-gradient(90deg, rgba(164,86,247,0.1) 0%, rgba(164,86,247,0.25) 50%, rgba(164,86,247,0.1) 100%)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 1.5s ease-in-out infinite',
                  border: '1px solid rgba(164,86,247,0.4)',
                }}
              >
                {/* Shimmer overlay */}
                <div 
                  className="absolute inset-0 -translate-x-full"
                  style={{
                    background: 'linear-gradient(90deg, transparent, rgba(164,86,247,0.3), transparent)',
                    animation: 'shimmerSlide 1.5s ease-in-out infinite',
                  }}
                />
                
                {/* Placeholder for checkbox area - pulsing dot */}
                <div className="flex items-center justify-center w-4 h-4">
                  <div 
                    className="w-3 h-3 rounded-full bg-blue-600 dark:bg-blue-400"
                    style={{ animation: 'pulse 1s ease-in-out infinite' }}
                  />
                </div>
                
                {/* PDF icon with glow effect */}
                <div 
                  className="relative shrink-0 w-10 h-10 rounded flex items-center justify-center"
                  style={{
                    background: 'linear-gradient(135deg, rgba(164,86,247,0.3) 0%, rgba(164,86,247,0.5) 100%)',
                    boxShadow: '0 0 15px rgba(164,86,247,0.4)',
                    animation: 'glow 1.5s ease-in-out infinite alternate',
                  }}
                >
                  <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                
                <div className="flex-1 min-w-0 relative z-10">
                  <p 
                    className="truncate text-sm font-medium"
                    style={{ 
                      color: '#3B82F6',
                      animation: 'textPulse 1.5s ease-in-out infinite',
                    }}
                  >
                    {file.name}
                  </p>
                  <p className="text-xs" style={{ color: 'rgba(164,86,247,0.7)' }}>
                    {file.error ? (
                      <span className="text-red-500">{file.error}</span>
                    ) : (
                      <span style={{ animation: 'textPulse 1.5s ease-in-out infinite 0.2s' }}>
                        {file.status || 'Processing...'}
                      </span>
                    )}
                  </p>
                </div>
              </div>
            ))}
            
            {/* CSS Keyframes for shimmer animations */}
            <style>{`
              @keyframes shimmer {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
              }
              @keyframes shimmerSlide {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
              }
              @keyframes glow {
                0% { box-shadow: 0 0 10px rgba(164,86,247,0.3); }
                100% { box-shadow: 0 0 20px rgba(164,86,247,0.6); }
              }
              @keyframes pulse {
                0%, 100% { opacity: 0.4; transform: scale(0.8); }
                50% { opacity: 1; transform: scale(1); }
              }
              @keyframes textPulse {
                0%, 100% { opacity: 0.7; }
                50% { opacity: 1; }
              }
            `}</style>
          </>
        )}
        
        {/* Loading state - only show when loading and no files */}
        {isLoadingPDFs && pdfFiles.length === 0 && uploadingFiles.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-8 h-8 border-4 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full animate-spin mb-2"></div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Loading PDFs...</p>
          </div>
        )}
        
        {/* Empty state - only show when no files and not uploading */}
        {pdfFiles.length === 0 && uploadingFiles.length === 0 && !isLoadingPDFs && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <svg className="w-12 h-12 text-gray-400 dark:text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <p className="text-xs text-gray-500 dark:text-gray-400">No PDF files uploaded yet</p>
          </div>
        )}
        
        {/* Uploaded files */}
        {pdfFiles.length > 0 && pdfFiles
              .filter((file) =>
                file.name.toLowerCase().includes(search.toLowerCase())
              )
              .map((file) => {
              return (
                <div
                  onMouseDown={(e) => {
                    e.stopPropagation();
                  }}
                  onClick={(e) => {
                    if (e.target.closest('input[type="checkbox"]') || e.target.closest('label')) {
                      return;
                    }
                    e.stopPropagation();
                  }}
                  key={file.id}
                  className="p-3 bg-gray-50/50 dark:bg-slate-800/40 border border-gray-200 dark:border-blue-500/20 rounded-md cursor-pointer flex items-center gap-3 group transition-all hover:border-blue-500 dark:hover:border-blue-500/40 hover:bg-blue-50/50 dark:hover:bg-slate-700/50"
                >
                  <label 
                    className="flex items-center cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePdfSelection(file.id);
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={file.isSelected || false}
                      onChange={(e) => {
                        e.stopPropagation();
                        togglePdfSelection(file.id);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded cursor-pointer border-2 transition-all focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-400"
                      style={{
                        backgroundColor: file.isSelected ? '#3B82F6' : 'transparent',
                        borderColor: file.isSelected ? '#3B82F6' : '#9CA3AF',
                        accentColor: '#3B82F6'
                      }}
                    />
                  </label>
                  <div className="flex-shrink-0 w-10 h-10 rounded bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                    <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    {editingPdfId === file.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveEdit(file.id);
                            } else if (e.key === 'Escape') {
                              handleCancelEdit();
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                          onBlur={() => handleSaveEdit(file.id)}
                          autoFocus
                          className="flex-1 text-sm font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-700 border border-blue-500 rounded px-2 py-1 outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    ) : (
                      <div 
                        className={`flex items-center gap-2 ${isAuthenticated ? 'group/edit' : ''}`}
                        onDoubleClick={isAuthenticated ? (e) => {
                          e.stopPropagation();
                          handleStartEdit(file.id, file.name);
                        } : undefined}
                      >
                        <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                          {file.name}
                        </p>
                        {isAuthenticated && (
                          <svg 
                            className="w-3 h-3 text-gray-400 dark:text-gray-500 opacity-0 group-hover/edit:opacity-100 cursor-pointer transition-opacity"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartEdit(file.id, file.name);
                            }}
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        )}
                      </div>
                    )}
                    <p className="text-xs text-gray-500 dark:text-[#B1A6C0]">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  {editingPdfId !== file.id && (
                    <img
                      src={assets.bin_icon}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePdf(file.id);
                      }}
                      className="hidden group-hover:block w-4 h-4 cursor-pointer not-dark:invert opacity-60 hover:opacity-100 transition-opacity"
                      alt=""
                    />
                  )}
                </div>
              );
            })}
      </div>
      {/* Community */}
      {/* <div
        onMouseDown={(e) => {
          e.stopPropagation();
          e.preventDefault();
        }}
        onMouseUp={(e) => {
          e.stopPropagation();
        }}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          navigate("/community");
        }}
        className="flex item-center gap-2 p-3 mt-4 border border-gray-300 dark:border-white/15 rounded-md cursor-pointer hover:scale-103 transition-all"
      >
        <img
          src={assets.gallery_icon}
          className="w-4.5 not-dark:invert"
          alt=""
          onMouseDown={(e) => e.stopPropagation()}
        />
        <div className="flex flex-col text-sm" onMouseDown={(e) => e.stopPropagation()}>
          <p>Community Images</p>
        </div>
      </div> */}
      {/* Crediet */}
      {/* <div
        onMouseDown={(e) => {
          e.stopPropagation();
          e.preventDefault();
        }}
        onMouseUp={(e) => {
          e.stopPropagation();
        }}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          navigate("/credits");
        }}
        className="flex item-center gap-2 p-3 mt-4 border border-gray-300 dark:border-white/15 rounded-md cursor-pointer hover:scale-103 transition-all"
      >
        <img 
          src={assets.diamond_icon} 
          className="w-4.5 dark:invert" 
          alt=""
          onMouseDown={(e) => e.stopPropagation()}
        />
        <div className="flex flex-col text-sm" onMouseDown={(e) => e.stopPropagation()}>
          <p>Credits : {user?.credits}</p>
          <p className="text-xs text-gray-400">
            Purchase credits to used ReadPDF AI
          </p>
        </div>
      </div> */}


      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

    </div>
  );
}


export default Sidebar;
