import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';
import { assets } from '../assets/assets';
import { motion } from 'framer-motion';
import RAGPipeline from '../components/RAGPipeline';

function Landing() {
  const navigate = useNavigate();
  const { theme } = useAppContext();
  const containerRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  
  // Cache container dimensions to avoid getBoundingClientRect on every frame
  const dimensionsRef = useRef({ width: 0, height: 0, left: 0, top: 0 });
  
  // Throttle mouse move updates
  const rafRef = useRef(null);
  const mouseRef = useRef({ x: 50, y: 50 });

  // Mark as loaded after initial render
  useEffect(() => {
    // Small delay to let the page settle
    const timer = setTimeout(() => setIsLoaded(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Cache dimensions on mount and resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        dimensionsRef.current = {
          width: rect.width,
          height: rect.height,
          left: rect.left,
          top: rect.top,
        };
      }
    };
    
    updateDimensions();
    window.addEventListener('resize', updateDimensions, { passive: true });
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Throttled mouse position update using RAF
  const updateMousePosition = useCallback(() => {
    document.documentElement.style.setProperty('--mouse-x', `${mouseRef.current.x}%`);
    document.documentElement.style.setProperty('--mouse-y', `${mouseRef.current.y}%`);
    rafRef.current = null;
  }, []);

  const handleMouseMove = useCallback((e) => {
    const dims = dimensionsRef.current;
    if (dims.width > 0) {
      mouseRef.current = {
        x: ((e.clientX - dims.left) / dims.width) * 100,
        y: ((e.clientY - dims.top) / dims.height) * 100,
      };
      
      // Throttle updates using RAF
      if (!rafRef.current) {
        rafRef.current = requestAnimationFrame(updateMousePosition);
      }
    }
  }, [updateMousePosition]);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = { x: 50, y: 50 };
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(updateMousePosition);
    }
  }, [updateMousePosition]);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', handleMouseMove, { passive: true });
      container.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    }
    return () => {
      if (container) {
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('mouseleave', handleMouseLeave);
      }
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [handleMouseMove, handleMouseLeave]);

  // Stagger animation variants for smooth entrance
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.4,
        when: "beforeChildren",
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: "easeOut" },
    },
  };

  return (
    <div
      ref={containerRef}
      className={`min-h-screen relative overflow-hidden dark:text-white transition-opacity duration-500 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
    >
      {/* Optimized Background - Pure CSS, no blur on large elements */}
      <div className="fixed inset-0 -z-10">
        {/* Dark Mode Background */}
        <div
          className="hidden dark:block absolute inset-0"
          style={{
            background: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 25%, #312e81 50%, #1e3a8a 75%, #0f172a 100%)',
          }}
        />
        
        {/* Light Mode Background */}
        <div
          className="dark:hidden absolute inset-0"
          style={{
            background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 20%, #e0e7ff 40%, #ffffff 60%, #e0e7ff 80%, #dbeafe 100%)',
          }}
        />
        
        {/* Mouse-following gradient - uses CSS variable, no blur */}
        <div
          className="absolute inset-0 pointer-events-none opacity-60 dark:opacity-40"
          style={{
            background: 'radial-gradient(circle 600px at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(59, 130, 246, 0.25) 0%, transparent 50%)',
            transition: 'background 0.3s ease-out',
          }}
        />
        
        {/* Optimized Glow Orbs - smaller blur, CSS animations */}
        <div
          className="absolute w-72 h-72 rounded-full pointer-events-none animate-float opacity-40 dark:opacity-20"
          style={{
            top: '15%',
            left: '10%',
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.5) 0%, transparent 70%)',
          }}
        />
        
        <div
          className="absolute w-80 h-80 rounded-full pointer-events-none opacity-30 dark:opacity-15"
          style={{
            top: '45%',
            right: '15%',
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.4) 0%, transparent 70%)',
            animation: 'float 10s ease-in-out infinite reverse',
          }}
        />
        
        <div
          className="absolute w-64 h-64 rounded-full pointer-events-none opacity-35 dark:opacity-20"
          style={{
            bottom: '20%',
            left: '30%',
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%)',
            animation: 'float 12s ease-in-out infinite 2s',
          }}
        />
      </div>
      
      <motion.div
        className="relative z-10"
        variants={containerVariants}
        initial="hidden"
        animate={isLoaded ? "visible" : "hidden"}
      >
        {/* Hero Section */}
        <div className="container mx-auto px-4 py-20">
          <motion.div
            className="max-w-4xl mx-auto text-center"
            variants={itemVariants}
          >
            <motion.img
              src={theme === 'dark' ? assets.logo_full : assets.logo_full_dark}
              alt="ReadPDF AI"
              className="w-full max-w-64 mx-auto mb-8"
              variants={itemVariants}
              whileHover={{ scale: 1.05 }}
              transition={{ type: 'spring', stiffness: 300 }}
            />
            <motion.h1
              className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 dark:from-blue-300 dark:via-blue-400 dark:to-blue-500 bg-clip-text text-transparent"
              variants={itemVariants}
            >
              Chat with Your PDF Documents
            </motion.h1>
            <motion.p
              className="text-xl md:text-2xl text-gray-800 dark:text-gray-200 mb-8 font-medium"
              variants={itemVariants}
            >
              Upload your PDF files and ask questions. Get instant answers powered by AI.
            </motion.p>
            <motion.button
              onClick={() => navigate('/chat')}
              className="bg-gradient-to-r from-blue-600 via-blue-500 to-blue-600 dark:from-blue-500 dark:via-blue-400 dark:to-blue-500 text-white px-8 py-4 rounded-full text-lg font-semibold shadow-lg hover:shadow-xl hover:shadow-blue-500/30 transition-all duration-300"
              variants={itemVariants}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Get Started
            </motion.button>
          </motion.div>
        </div>

        {/* Features Section */}
        <div className="container mx-auto px-4 py-16">
          <motion.div
            className="max-w-6xl mx-auto"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 dark:from-blue-300 dark:via-blue-400 dark:to-blue-500 bg-clip-text text-transparent">
              Features
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  icon: (
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  ),
                  title: 'Easy Upload',
                  description: 'Simply drag and drop your PDF files or click to browse. Support for multiple PDFs at once.',
                },
                {
                  icon: (
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  ),
                  title: 'AI-Powered Chat',
                  description: 'Ask questions about your PDF documents and get accurate, context-aware answers instantly.',
                },
                {
                  icon: (
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  ),
                  title: 'Privacy First',
                  description: 'Your documents are processed securely. No data is stored permanently on our servers.',
                },
              ].map((feature, index) => (
                <motion.div
                  key={index}
                  className="p-6 rounded-xl border border-blue-200/60 dark:border-blue-500/30 bg-white/90 dark:bg-slate-900/70 shadow-sm hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300"
                  initial={{ y: 30, opacity: 0 }}
                  whileInView={{ y: 0, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                  whileHover={{ y: -5 }}
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 dark:from-blue-400 dark:via-blue-500 dark:to-blue-600 flex items-center justify-center mb-4 shadow-lg">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-2 text-gray-800 dark:text-white">{feature.title}</h3>
                  <p className="text-gray-700 dark:text-gray-300">{feature.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Architecture Section */}
        <div className="container mx-auto px-4 py-16">
          <motion.div
            className="max-w-7xl mx-auto"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6 }}
          >
            {/* Header */}
            <div className="text-center mb-12">
              <div className="inline-block px-4 py-1.5 mb-6 text-sm font-semibold tracking-wider text-blue-600 dark:text-blue-300 uppercase bg-blue-100 dark:bg-blue-900/50 rounded-full">
                System Architecture
              </div>
              
              <h2 className="text-3xl md:text-4xl font-bold mb-6 text-gray-900 dark:text-white leading-tight">
                Beyond Simple Text Search with{' '}
                <span className="bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">
                  Multi-Modal RAG
                </span>
              </h2>
              
              <p className="text-lg text-gray-700 dark:text-gray-300 max-w-3xl mx-auto leading-relaxed">
                ระบบของเราไม่ได้แค่อ่านตัวหนังสือ แต่เข้าใจบริบทของเอกสารทั้งฉบับ ด้วยกระบวนการประมวลผลขั้นสูง
              </p>
            </div>

            {/* Feature Cards */}
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              {[
                {
                  title: "Image Understanding",
                  desc: "ใช้โมเดล LLaVA/Llama แปลงภาพในเอกสารให้เป็นคำบรรยาย เพื่อให้ค้นหาข้อมูลในรูปภาพได้",
                  icon: "🖼️",
                  color: "from-yellow-500/20 to-orange-500/20 border-yellow-500/30"
                },
                {
                  title: "Table Parsing",
                  desc: "แปลงตารางซับซ้อนให้อยู่ในรูปแบบ HTML Format เพื่อรักษาโครงสร้างข้อมูลให้แม่นยำที่สุด",
                  icon: "📊",
                  color: "from-cyan-500/20 to-blue-500/20 border-cyan-500/30"
                },
                {
                  title: "Vector Search & Retrieval",
                  desc: "จัดเก็บข้อมูลในรูปแบบ Vector DB ทำให้ค้นหาคำตอบที่เกี่ยวข้องที่สุดได้อย่างรวดเร็ว",
                  icon: "⚡",
                  color: "from-purple-500/20 to-pink-500/20 border-purple-500/30"
                }
              ].map((item, i) => (
                <motion.div 
                  key={i}
                  className={`p-6 rounded-2xl bg-gradient-to-br ${item.color} border backdrop-blur-sm`}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 + (i * 0.1) }}
                >
                  <div className="text-4xl mb-4">{item.icon}</div>
                  <h4 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-2">{item.title}</h4>
                  <p className="text-gray-600 dark:text-gray-400 text-sm">{item.desc}</p>
                </motion.div>
              ))}
            </div>

            {/* RAG Pipeline Diagram */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="overflow-x-auto"
            >
              <RAGPipeline 
                onLlamaClick={() => window.open('https://llama.meta.com/', '_blank')}
                className="min-w-[900px]"
              />
            </motion.div>

            {/* Floating Powered By Label */}
            <motion.div 
              className="flex justify-center mt-6"
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 }}
            >
              <div className="bg-white dark:bg-slate-800 px-6 py-3 rounded-full shadow-lg border border-blue-100 dark:border-slate-700">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="font-semibold text-sm text-gray-700 dark:text-gray-200">Powered by Llama 3 & Llama 4 Vision</span>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* How It Works Section */}
        <div className="container mx-auto px-4 py-16">
          <motion.div
            className="max-w-4xl mx-auto"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 dark:from-blue-300 dark:via-blue-400 dark:to-blue-500 bg-clip-text text-transparent">
              How It Works
            </h2>
            <div className="space-y-8">
              {[
                {
                  number: '1',
                  title: 'Upload PDF Files',
                  description: 'Drag and drop your PDF files or click to browse. You can upload multiple PDFs and select which ones to use for your chat.',
                },
                {
                  number: '2',
                  title: 'Select PDFs',
                  description: 'Choose which PDF files you want to chat with by checking the boxes next to each file.',
                },
                {
                  number: '3',
                  title: 'Start Chatting',
                  description: 'Ask questions about your PDF documents and get instant, accurate answers powered by AI.',
                },
              ].map((step, index) => (
                <motion.div
                  key={index}
                  className="flex items-start gap-4 group"
                  initial={{ x: -30, opacity: 0 }}
                  whileInView={{ x: 0, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 dark:from-blue-400 dark:via-blue-500 dark:to-blue-600 flex items-center justify-center text-white font-bold shadow-md group-hover:scale-110 transition-transform duration-300">
                    {step.number}
                  </div>
                  <div className="group-hover:translate-x-2 transition-transform duration-300">
                    <h3 className="text-xl font-semibold mb-2 text-gray-800 dark:text-white">{step.title}</h3>
                    <p className="text-gray-700 dark:text-gray-300">{step.description}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}

export default Landing;
