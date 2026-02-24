import React, { useEffect, useRef, useState } from "react";
import { useAppContext } from "../context/AppContext";
import { useAuth } from "../context/AuthContext";
import { assets } from "../assets/assets";
import Message from "./Message";
import { chatWithPDF, getChatHistory, saveChatHistory } from "../services/api";
import { loadGuestData, saveGuestData, clearExpiredGuestData } from "../utils/guestDataManager";

function ChatBox() {
  const { pdfFiles, theme, aiAvatar } = useAppContext();
  const { isAuthenticated, token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const containerRef = useRef(null);
  const abortControllerRef = useRef(null);
  
  // Load chat history when authenticated
  useEffect(() => {
    const loadHistory = async () => {
      if (isAuthenticated && token) {
        try {
          setIsLoadingHistory(true);
          const response = await getChatHistory(token);
          if (response.success && response.chat_history) {
            setMessages(response.chat_history);
          }
        } catch (error) {
          console.error('Failed to load chat history:', error);
          // Fallback to guest data if available
          const saved = loadGuestData('guest_chat_messages');
          if (saved) {
            setMessages(saved);
          }
        } finally {
          setIsLoadingHistory(false);
        }
      } else {
        // Guest mode - load from localStorage with auto-expiry (1 day)
        clearExpiredGuestData(); // Clear expired data first
        
        if (typeof window !== 'undefined') {
          const saved = loadGuestData('guest_chat_messages');
          if (saved && Array.isArray(saved)) {
            setMessages(saved);
          } else {
            setMessages([]);
          }
        }
      }
    };
    
    loadHistory();
  }, [isAuthenticated, token]);
  
  // Save chat history when authenticated
  const saveHistory = async (updatedMessages) => {
    if (isAuthenticated && token) {
      try {
        await saveChatHistory(token, updatedMessages);
      } catch (error) {
        console.error('Failed to save chat history:', error);
      }
    } else {
      // Guest mode - save to localStorage with timestamp (expires in 1 day)
      if (typeof window !== 'undefined') {
        saveGuestData('guest_chat_messages', updatedMessages);
      }
    }
  };

  const selectedPdfIds = pdfFiles.filter(pdf => pdf.isSelected).map(pdf => pdf.id);
  
  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
      
      // Add a stopped message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Generation stopped by user.',
        timestamp: Date.now(),
        isStopped: true,
      }]);
    }
  };

  const sendMessage = async (messageContent, isEdit = false, editIndex = null) => {
    if (!messageContent.trim() || selectedPdfIds.length === 0) return;
    
    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();
    
    const userMessage = {
      role: 'user',
      content: messageContent,
      timestamp: Date.now(),
    };
    
    let updatedMessages;
    if (isEdit && editIndex !== null) {
      updatedMessages = [...messages.slice(0, editIndex), userMessage];
    } else {
      updatedMessages = [...messages, userMessage];
    }
    setMessages(updatedMessages);
    await saveHistory(updatedMessages);
    
    setPrompt("");
    setLoading(true);
    
    try {
      // Prepare chat history (only user and assistant messages, no system messages)
      const chatHistoryForAPI = updatedMessages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp ? String(msg.timestamp) : undefined
        }))
        .filter(msg => msg.content); // Remove empty messages
      
      const response = await chatWithPDF(
        messageContent, 
        selectedPdfIds, 
        abortControllerRef.current.signal,
        chatHistoryForAPI
      );
      
      const aiMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: Date.now(),
        sources: response.sources || [],
      };
      
      const finalMessages = [...updatedMessages, aiMessage];
      setMessages(finalMessages);
      await saveHistory(finalMessages);
    } catch (error) {
      if (error.message === 'Request cancelled') return;
      const errorMessage = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        timestamp: Date.now(),
        isError: true,
      };
      const messagesWithError = [...updatedMessages, errorMessage];
      setMessages(messagesWithError);
      await saveHistory(messagesWithError);
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    await sendMessage(prompt);
  };

  const handleEditMessage = (index) => (newContent) => {
    sendMessage(newContent, true, index);
  };
  
  useEffect(()=>{
    if(containerRef.current){
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior:'smooth',
      })
    }
  }, [messages])

  return (
    <div className='flex-1 flex flex-col justify-between rounded-xl bg-white/80 dark:bg-slate-800/60 backdrop-blur-sm border border-gray-200 dark:border-blue-500/20 shadow-lg overflow-hidden h-full'>
      <div className='flex-1 flex flex-col justify-between p-5 md:p-10 xl:px-30 max-md:mt-14 2xl:pr-40 h-full'>
        {/* Chat Messages */}
        <div ref={containerRef} className='flex-1 mb-5 overflow-y-scroll'>
          {messages.length === 0 && (
            <div className='h-full flex flex-col items-center justify-center gap-2 text-primary'>
              <img src={theme === 'dark' ? assets.logo_full : assets.logo_full_dark} alt="" className='w-full max-w-56 sm:max-w-68'/>
              {selectedPdfIds.length === 0 ? (
                <>
                  <p className='mt-5 text-2xl sm:text-4xl text-center text-gray-400 dark:text-white font-medium'>Upload and select PDF files</p>
                  <p className='text-sm text-gray-500 dark:text-gray-400 text-center mt-2'>Select PDF files from the sidebar to start chatting</p>
                </>
              ) : (
                <>
                  <p className='mt-5 text-2xl sm:text-4xl text-center text-gray-400 dark:text-white font-medium'>Ask me about your PDF</p>
                  <p className='text-sm text-gray-500 dark:text-gray-400 text-center mt-2'>I can answer questions about your documents or general knowledge</p>
                </>
              )}
            </div>
          )}

          {messages.map((message, index) => (
            <Message 
              key={message.timestamp ? `msg-${message.timestamp}-${index}` : `msg-${index}`}
              message={message}
              canEdit={message.role === 'user' && !loading}
              onEdit={handleEditMessage(index)}
            />
          ))}

          {/* AI Loading with Avatar */}
          {
            loading && (
              <div className='flex items-start justify-start my-4 gap-3'>
                <img 
                  src={aiAvatar || assets.user_icon} 
                  alt="AI" 
                  className='w-8 h-8 mt-4 rounded-full object-cover'
                />
                <div className='inline-flex items-center gap-2 p-3 px-4 bg-blue-50 dark:bg-blue-500/20 border border-blue-200 dark:border-blue-500/30 rounded-md my-4'>
                  <div className='flex items-center gap-1.5'>
                    <div className='w-2 h-2 rounded-full bg-blue-600 dark:bg-blue-400 animate-bounce'></div>
                    <div className='w-2 h-2 rounded-full bg-blue-600 dark:bg-blue-400 animate-bounce' style={{animationDelay: '0.1s'}}></div>
                    <div className='w-2 h-2 rounded-full bg-blue-600 dark:bg-blue-400 animate-bounce' style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span className='text-sm text-gray-500 dark:text-gray-400 ml-2'>Thinking...</span>
                </div>
              </div>
            )
          }
        </div>

        {/* Prompt Input Box */}
        <form onSubmit={onSubmit} className='bg-blue-50 dark:bg-blue-500/20 border border-blue-200 dark:border-blue-500/30 rounded-full w-full max-w-2xl p-3 pl-4 mx-auto flex gap-4 items-center'>
          <input 
            onChange={(e)=>setPrompt(e.target.value)} 
            value={prompt} 
            type="text" 
            placeholder={selectedPdfIds.length > 0 ? "Ask about your PDF or any general question..." : "Select PDF files to start chatting..."} 
            className='flex-1 w-full text-sm outline-none bg-transparent' 
            required
            disabled={selectedPdfIds.length === 0 || loading}
          />
          {loading ? (
            <button 
              type="button"
              onClick={stopGeneration}
              className='cursor-pointer hover:opacity-80 transition-opacity'
              title="Stop generation"
            >
              <div className='w-8 h-8 flex items-center justify-center bg-white dark:bg-white/90 hover:bg-white/80 rounded-full transition-colors'>
                <svg className="w-4 h-4 text-gray-800 dark:text-gray-800" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
              </div>
            </button>
          ) : (
            <button 
              type="submit"
              disabled={selectedPdfIds.length === 0 || !prompt.trim()}
              className={`${selectedPdfIds.length === 0 || !prompt.trim() ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:opacity-80 transition-opacity'}`}
            >
              <div className='w-8 h-8 flex items-center justify-center bg-white dark:bg-white/90 hover:bg-white/80 rounded-full transition-colors'>
                <svg className="w-4 h-4 text-gray-800 dark:text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              </div>
            </button>
          )}
        </form>
      </div>
    </div>
  )
}

export default ChatBox;
