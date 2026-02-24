import { useState, useEffect } from 'react'
import {Routes, Route, useLocation} from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ChatBox from './components/ChatBox'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import GoogleCallback from './pages/GoogleCallback'
import Navbar from './components/Navbar'
import './assets/prism.css'
import Loading from './pages/Loading'
import { useAppContext } from './context/AppContext'
import { clearExpiredGuestData } from './utils/guestDataManager'

const App = () => {
  const {pathname} = useLocation()
  const {theme} = useAppContext()
  const [activeTab, setActiveTab] = useState('chat') // 'source' or 'chat'
  const [isMobile, setIsMobile] = useState(false)

  // Clear expired guest data on app load
  useEffect(() => {
    clearExpiredGuestData();
  }, []);

  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 1050)
    }
    
    checkScreenSize()
    window.addEventListener('resize', checkScreenSize)
    
    return () => window.removeEventListener('resize', checkScreenSize)
  }, [])

  if(pathname === '/loading') return <Loading/>

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark:bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 dark:text-white' : 'bg-gradient-to-b from-slate-50 via-white to-slate-50 text-gray-900'}`}>
      <Navbar />
        <Routes>
        <Route path='/' element={<Landing />} />
        <Route path='/auth' element={<Auth />} />
        <Route path='/auth/google/callback' element={<GoogleCallback />} />
        <Route path='/chat' element={
          <div className='flex flex-col h-[calc(100vh-4rem)]'>
            {/* Tab Bar for mobile/small screens */}
            {isMobile && (
              <div className='flex border-b border-gray-200 dark:border-blue-500/30 bg-white/50 dark:bg-slate-800/50'>
                <button
                  onClick={() => setActiveTab('source')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'source'
                      ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-500/20'
                      : 'text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'
                  }`}
                >
                  Source
                </button>
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'chat'
                      ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-500/20'
                      : 'text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'
                  }`}
                >
                  Chat
                </button>
      </div>
            )}

            {/* Content Area */}
            <div className={`flex-1 flex gap-4 px-4 py-4 min-h-0 ${isMobile ? 'overflow-hidden' : ''}`}>
              {/* Sidebar - Show on desktop or when source tab is active on mobile */}
              {(!isMobile || activeTab === 'source') && (
                <div className={isMobile ? 'w-full h-full min-h-0' : 'h-full'}>
                  <Sidebar isTabMode={isMobile} />
      </div>
    )}

              {/* ChatBox - Show on desktop or when chat tab is active on mobile */}
              {(!isMobile || activeTab === 'chat') && (
                <div className={isMobile ? 'w-full h-full min-h-0' : 'flex-1 h-full min-h-0'}>
                  <ChatBox />
                </div>
              )}
            </div>
          </div>
        } />
      </Routes>
    </div>
  )
}

export default App
