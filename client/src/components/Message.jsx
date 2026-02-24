import React, { useEffect, useState, useRef } from 'react'
import { assets } from '../assets/assets'
import moment from 'moment'
import Markdown from 'react-markdown'
import Prism from 'prismjs'
import { useAppContext } from '../context/AppContext'

const Message = ({message, onEdit, canEdit = false}) => {
  const { aiAvatar, setAiAvatar, userAvatar, setUserAvatar } = useAppContext();
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const fileInputRef = useRef(null);
  const userAvatarInputRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(()=>{
    Prism.highlightAll()
  },[message.content])

  // Auto-resize textarea when editing
  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = 'auto';
      // Set height based on content, with min and max constraints
      const scrollHeight = textareaRef.current.scrollHeight;
      const minHeight = 60; // Minimum height
      const maxHeight = 400; // Maximum height before scrolling
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, minHeight), maxHeight)}px`;
    }
  };

  useEffect(() => {
    if (isEditing) {
      adjustTextareaHeight();
    }
  }, [isEditing])

  useEffect(() => {
    if (isEditing && editContent) {
      adjustTextareaHeight();
    }
  }, [editContent, isEditing])

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please upload an image file');
        return;
      }
      // Validate file size (max 2MB)
      if (file.size > 2 * 1024 * 1024) {
        alert('Image size should be less than 2MB');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (event) => {
        setAiAvatar(event.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUserAvatarClick = () => {
    userAvatarInputRef.current?.click();
  };

  const handleUserAvatarUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please upload an image file');
        return;
      }
      // Validate file size (max 2MB)
      if (file.size > 2 * 1024 * 1024) {
        alert('Image size should be less than 2MB');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (event) => {
        setUserAvatar(event.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    if (editContent.trim() && onEdit) {
      onEdit(editContent.trim());
      setIsEditing(false);
    }
  };

  const handleCancelEdit = () => {
    setEditContent(message.content);
    setIsEditing(false);
  };

  return (
    <div>
      {message.role === "user" ? (
        <div className='flex items-start justify-end my-4 gap-3'>
          <div className='flex flex-col gap-2 p-2 px-4 bg-slate-50 dark:bg-blue-500/20 border border-blue-200 dark:border-blue-500/30 rounded-md max-w-2xl w-full group'>
            {isEditing ? (
              <form onSubmit={handleEditSubmit} className='flex flex-col gap-2 w-full'>
                <textarea
                  ref={textareaRef}
                  value={editContent}
                  onChange={(e) => {
                    setEditContent(e.target.value);
                    adjustTextareaHeight();
                  }}
                  onInput={adjustTextareaHeight}
                  className='w-full text-sm dark:text-blue-200 bg-white dark:bg-slate-700 border border-gray-300 dark:border-blue-500/50 rounded-md p-3 min-h-[60px] max-h-[400px] resize-none outline-none focus:border-blue-600 dark:focus:border-blue-400 overflow-y-auto'
                  autoFocus
                  style={{ 
                    height: 'auto',
                    minHeight: '60px',
                    maxHeight: '400px'
                  }}
                />
                <div className='flex gap-2 justify-end'>
                  <button
                    type='button'
                    onClick={handleCancelEdit}
                    className='text-xs px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors'
                  >
                    Cancel
                  </button>
                  <button
                    type='submit'
                    disabled={!editContent.trim()}
                    className='text-xs px-3 py-1 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
                  >
                    Send
                  </button>
                </div>
              </form>
            ) : (
              <>
                <p className='text-sm text-gray-800 dark:text-white'>{message.content}</p>
                <div className='flex items-center justify-between gap-2'>
                  <span className='text-xs text-gray-400 dark:text-[#B1A6C0]'>
                    {moment(message.timestamp).fromNow()}
                  </span>
                  {canEdit && (
                    <button
                      onClick={() => setIsEditing(true)}
                      className='opacity-0 group-hover:opacity-100 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-all flex items-center gap-1'
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Edit
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
          {/* User Avatar - clickable to upload */}
          <div className="relative group">
            <input
              type="file"
              ref={userAvatarInputRef}
              onChange={handleUserAvatarUpload}
              accept="image/*"
              className="hidden"
            />
            <img 
              src={userAvatar || assets.user_icon} 
              alt="User" 
              className='w-8 h-8 rounded-full cursor-pointer object-cover hover:opacity-80 transition-opacity'
              onClick={handleUserAvatarClick}
            />
            {/* Upload hint overlay */}
            <div 
              className="absolute inset-0 w-8 h-8 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
              onClick={handleUserAvatarClick}
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
          </div>
        </div>
      )
      : 
      (
        <div className="flex items-start justify-start my-4 gap-3">
          {/* AI Avatar - clickable to upload */}
          <div className="relative group">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleAvatarUpload}
              accept="image/*"
              className="hidden"
            />
            <img 
              src={aiAvatar || assets.user_icon} 
              alt="AI" 
              className='w-8 h-8 mt-4 rounded-full cursor-pointer object-cover hover:opacity-80 transition-opacity'
              onClick={handleAvatarClick}
            />
            {/* Upload hint overlay */}
            <div 
              className="absolute inset-0 mt-4 w-8 h-8 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
              onClick={handleAvatarClick}
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
          </div>
          
          <div className='inline-flex flex-col gap-2 p-2 px-4 max-w-2xl bg-blue-50 dark:bg-blue-500/20 border border-blue-200 dark:border-blue-500/30 rounded-md my-4'>
            {message.isImage ? (
              <img src={message.content} alt="" className='w-full max-w-md mt-2 rounded-md'/>
            ):
            (
              <div className='text-sm text-gray-800 dark:text-white reset-tw'>
              <Markdown>{message.content}</Markdown></div>
            )}
            {/* Show error indicator */}
            {message.isError && (
              <div className="mt-1 text-xs text-red-500 dark:text-red-400">
                ⚠️ Error occurred
              </div>
            )}
            <span className='text-xs text-gray-400 dark:text-[#B1A6C0]'>{moment(message.timestamp).fromNow()}</span>
          </div>
        </div>
      )
    }
    </div>
  )
}

export default Message
