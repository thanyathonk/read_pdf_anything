import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Image as ImageIcon, 
  Table as TableIcon, 
  FileText, 
  Database, 
  Search, 
  Layers,
  User,
  Cpu,
  ChevronRight,
  Sparkles,
  Zap,
} from 'lucide-react';

// ============================================
// 1. SYSTEM COORDINATES (UNCHANGED)
// ============================================
const LAYOUT = {
  idx_w: 1200,
  idx_h: 400,
  ret_w: 1200,
  ret_h: 400,
};

const R = {
  sm: 32, md: 40, lg: 48, xl: 56,
};

const IDX = {
  col_docs: 100,
  col_input: 350,
  col_process: 600,
  col_output: 800,
  col_embed: 980,
  col_db: 1120,
  row_top: 80,
  row_mid: 200,
  row_bot: 330,
};

const RET = {
  col_query: 100,
  col_vec: 300,
  col_ret: 500,
  col_topk: 700,
  col_llm: 900,
  col_resp: 1100,
  row_main: 200,
  row_top: 120,
  row_bot: 280,
};

// ============================================
// 2. HELPER COMPONENTS (STYLED FOR LIGHT/DARK)
// ============================================

const Tooltip = ({ text, children }) => {
    const [show, setShow] = useState(false);
    
    if (!text) return children;
  
    return (
      <div 
        className="relative flex items-center justify-center" 
        onMouseEnter={() => setShow(true)} 
        onMouseLeave={() => setShow(false)}
      >
        {children}
        
        {show && (
          <motion.div 
            initial={{ opacity: 0, y: 5, scale: 0.9 }} 
            animate={{ opacity: 1, y: -12, scale: 1 }}
            transition={{ duration: 0.2, type: "spring", stiffness: 300 }}
            className="absolute bottom-full mb-2 z-[100]"
          >
            {/* Light Mode: white bg + shadow | Dark Mode: slate-900 */}
            <div className="relative px-4 py-2 
              bg-white dark:bg-slate-900/95 
              text-slate-700 dark:text-slate-100 
              text-xs font-medium rounded-xl 
              border border-slate-200 dark:border-slate-600 
              shadow-lg dark:shadow-none
              backdrop-blur-md whitespace-nowrap"
            >
              <span className="relative z-10">{text}</span>
              
              {/* Gradient effect (dark mode only) */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/0 dark:from-blue-500/10 to-cyan-500/0 dark:to-cyan-500/10 pointer-events-none" />
              
              {/* Arrow */}
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 
                bg-white dark:bg-slate-900/95 
                border-r border-b border-slate-200 dark:border-slate-600 
                rotate-45"
              />
            </div>
          </motion.div>
        )}
      </div>
    );
  };

const Node = ({ x, y, size = 'md', color = 'blue', icon: Icon, label, sublabel, onClick, tooltip, children }) => {
  const sizeClass = { sm: 'w-16 h-16', md: 'w-20 h-20', lg: 'w-24 h-24', xl: 'w-28 h-28' };
  const iconSize = { sm: 20, md: 24, lg: 32, xl: 40 };
  
  // Light & Dark mode colors (Blue-Cyan theme, no purple)
  const colors = {
    red: 'bg-red-500/10 dark:bg-red-500/10 border-red-400/40 dark:border-red-500/50 text-red-500 dark:text-red-400',
    blue: 'bg-blue-500/10 dark:bg-blue-500/10 border-blue-400/40 dark:border-blue-500/50 text-blue-500 dark:text-blue-400',
    sky: 'bg-sky-500/10 dark:bg-sky-500/10 border-sky-400/40 dark:border-sky-500/50 text-sky-500 dark:text-sky-400',
    yellow: 'bg-yellow-500/10 dark:bg-yellow-500/10 border-yellow-400/40 dark:border-yellow-500/50 text-yellow-600 dark:text-yellow-400',
    green: 'bg-green-500/10 dark:bg-green-500/10 border-green-400/40 dark:border-green-500/50 text-green-500 dark:text-green-400',
    cyan: 'bg-cyan-500/10 dark:bg-cyan-500/10 border-cyan-400/40 dark:border-cyan-500/50 text-cyan-500 dark:text-cyan-400',
    orange: 'bg-orange-500/10 dark:bg-orange-500/10 border-orange-400/40 dark:border-orange-500/50 text-orange-500 dark:text-orange-400',
    teal: 'bg-teal-500/10 dark:bg-teal-500/10 border-teal-400/40 dark:border-teal-500/50 text-teal-500 dark:text-teal-400',
  };

  return (
    <div className="absolute z-20" style={{ left: x, top: y, transform: 'translate(-50%, -50%)' }}>
      <Tooltip text={tooltip}>
        <motion.div 
          onClick={onClick}
          whileTap={onClick ? { scale: 0.95 } : {}}
          className={`
            ${sizeClass[size]} ${colors[color]} 
            border rounded-2xl flex flex-col items-center justify-center 
            backdrop-blur-md shadow-lg 
            transition-all duration-200
            ${onClick ? 'cursor-pointer hover:bg-white/10 dark:hover:bg-white/5 hover:shadow-xl' : ''}
          `}
        >
          {children || (Icon && <Icon size={iconSize[size]} />)}
          {(label || sublabel) && (
            <div className="absolute top-full mt-2 text-center w-32 pointer-events-none">
              {label && <div className="text-sm font-bold text-slate-700 dark:text-slate-200 drop-shadow-sm dark:drop-shadow-md">{label}</div>}
              {sublabel && <div className="text-xs text-slate-500 dark:text-slate-400">{sublabel}</div>}
            </div>
          )}
        </motion.div>
      </Tooltip>
    </div>
  );
};

// Mobile Swipe Hint Component
const MobileHint = () => (
  <motion.div 
    className="flex md:hidden items-center justify-center gap-2 py-3 text-sm text-slate-500 dark:text-slate-400"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: 0.5 }}
  >
    <span>Scaled view • Swipe to explore</span>
    <motion.div
      animate={{ x: [0, 6, 0] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
    >
      <ChevronRight size={18} />
    </motion.div>
  </motion.div>
);

// ============================================
// 3. PATH ENGINE (UNCHANGED)
// ============================================

const calculatePath = (x1, y1, x2, y2) => {
    const dist = Math.abs(x2 - x1);
    const controlPointOffset = dist * 0.5;
    return `M ${x1} ${y1} C ${x1 + controlPointOffset} ${y1}, ${x2 - controlPointOffset} ${y2}, ${x2} ${y2}`;
};
  
const calculateDetourPath = (x1, y1, x2, y2, xBreak) => {
    const lineToBreak = `L ${xBreak} ${y1}`;
    const dist = Math.abs(x2 - xBreak);
    const controlOffset = dist * 0.5;
    const curveToTarget = `C ${xBreak + controlOffset} ${y1}, ${x2 - controlOffset} ${y2}, ${x2} ${y2}`;
    return `M ${x1} ${y1} ${lineToBreak} ${curveToTarget}`;
};

const ConnectionLayer = ({ width, height, paths, idPrefix }) => (
    <svg className="absolute inset-0 z-10 pointer-events-none" width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        {paths.map((p, i) => (
          <marker 
            key={`marker-${i}`}
            id={`arrow-${idPrefix}-${i}`}
            markerWidth="6" 
            markerHeight="6" 
            refX="5" 
            refY="3" 
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6" fill={p.color || "#64748b"} />
          </marker>
        ))}
      </defs>
      
      {paths.map((p, i) => (
        <React.Fragment key={i}>
          {/* Layer 1: Background line */}
          <path 
            d={p.d} 
            fill="none" 
            stroke={p.color || "#64748b"} 
            strokeWidth="3"  
            strokeOpacity="0.1" 
            strokeLinecap="round"
          />
  
          {/* Layer 2: Flowing animation line */}
          <motion.path
            d={p.d}
            fill="none"
            stroke={p.color || "#38bdf8"}
            strokeWidth="3" 
            strokeLinecap="round"
            markerEnd={`url(#arrow-${idPrefix}-${i})`}
            initial={{ strokeDashoffset: 0 }}
            animate={{ strokeDashoffset: -20 }} 
            transition={{
              duration: 1, 
              repeat: Infinity,
              ease: "linear"
            }}
            style={{
               strokeDasharray: "10 10", 
               opacity: 1 
            }}
          />
          
          {/* Layer 3: Data particle */}
          <motion.circle 
            r="4" 
            fill="#ffffff"
            style={{ offsetPath: `path('${p.d}')` }}
            animate={{ offsetDistance: ["0%", "100%"] }}
            transition={{ duration: p.duration || 2.5, repeat: Infinity, ease: "linear", delay: p.delay || 0 }}
            className="drop-shadow-md"
          />
        </React.Fragment>
      ))}
    </svg>
  );

// ============================================
// 4. PIPELINE SECTIONS (STYLED FOR LIGHT/DARK)
// ============================================

const IndexingPipeline = ({ onLlamaClick }) => {
  const paths = [
    { d: calculatePath(IDX.col_docs + R.lg, IDX.row_mid, IDX.col_input - R.sm, IDX.row_top), color: "#0ea5e9" }, // sky
    { d: calculatePath(IDX.col_docs + R.lg, IDX.row_mid, IDX.col_input - R.sm, IDX.row_mid), color: "#3b82f6" }, // blue
    { d: calculatePath(IDX.col_docs + R.lg, IDX.row_mid, IDX.col_input - R.sm, IDX.row_bot), color: "#22c55e" }, // green
    { 
        d: calculateDetourPath(
          IDX.col_input + R.sm,
          IDX.row_top, 
          IDX.col_embed - R.lg,
          IDX.row_mid, 
          IDX.col_output + 20
        ), 
        color: "#0ea5e9", // sky
        delay: 1.5 
      },
    { d: calculatePath(IDX.col_input + R.sm, IDX.row_mid, IDX.col_process - R.md, IDX.row_mid), color: "#3b82f6", delay: 0.5 }, // blue
    { d: calculatePath(IDX.col_process + R.md, IDX.row_mid, IDX.col_output - R.sm, IDX.row_mid), color: "#eab308", delay: 1.5 }, // yellow
    { d: calculatePath(IDX.col_output + R.sm, IDX.row_mid, IDX.col_embed - R.lg, IDX.row_mid), color: "#eab308", delay: 2.5 }, // yellow
    { d: calculatePath(IDX.col_input + R.sm, IDX.row_bot, IDX.col_process - R.md, IDX.row_bot), color: "#22c55e", delay: 0.5 }, // green
    { 
        d: calculateDetourPath(
          IDX.col_process + R.md,
          IDX.row_bot, 
          IDX.col_embed - R.lg,
          IDX.row_mid, 
          IDX.col_output + 20
        ), 
        color: "#06b6d4", // cyan
        delay: 1.5 
      },
    { d: calculatePath(IDX.col_embed + R.lg, IDX.row_mid, IDX.col_db - R.lg, IDX.row_mid), color: "#14b8a6", delay: 3 }, // teal
  ];

  return (
    <div className="relative w-[1200px] h-[430px] 
      bg-white/60 dark:bg-slate-800/40 
      rounded-3xl 
      border border-slate-200 dark:border-slate-700 
      mb-8 overflow-hidden
      shadow-sm dark:shadow-none"
    >
      <div className="absolute top-4 left-6 text-sm font-bold 
        text-slate-500 dark:text-slate-400 
        tracking-widest uppercase"
      >
        Pipeline: Data Indexing
      </div>
      
      <ConnectionLayer width={LAYOUT.idx_w} height={LAYOUT.idx_h} paths={paths} idPrefix="idx" />

      {/* Nodes */}
      <Node x={IDX.col_docs} y={IDX.row_mid} size="lg" color="red" icon={FileText} label="Documents" 
        tooltip="Raw Multi-modal PDF Source" 
      />
      <Node x={IDX.col_input} y={IDX.row_top} size="sm" color="sky" icon={FileText} label="Text Chunks" 
        tooltip="Text Segmentation & Splitting" 
      />
      <Node x={IDX.col_input} y={IDX.row_mid} size="sm" color="blue" icon={ImageIcon} label="Images" 
        tooltip="Visual Artifact Extraction" 
      />
      <Node x={IDX.col_input} y={IDX.row_bot} size="sm" color="green" icon={TableIcon} label="Tables" 
        tooltip="Tabular Data Extraction" 
      />
      <Node x={IDX.col_process} y={IDX.row_mid} size="md" color="yellow" label="Llama 4" sublabel="Captioning" onClick={onLlamaClick}
        tooltip="Visual Analysis & Captioning Model" 
      >
        <div className="font-bold text-lg">∞</div>
      </Node>
      <Node x={IDX.col_process} y={IDX.row_bot} size="md" color="cyan" label="HTML" sublabel="Format"
        tooltip="Structure Preservation (HTML Format)" 
      >
        <div className="font-mono text-xs">&lt;/&gt;</div>
      </Node>
      <Node x={IDX.col_output} y={IDX.row_mid} size="sm" color="sky" icon={FileText} label="Text Chunks" 
        tooltip="Enriched Context Chunks" 
      />
      <Node x={IDX.col_embed} y={IDX.row_mid} size="lg" color="teal" icon={Layers} label="Embeddings" 
        tooltip="High-Dimensional Vectorization" 
      />
      <Node x={IDX.col_db} y={IDX.row_mid} size="lg" color="blue" icon={Database} label="Vector DB" 
        tooltip="Semantic Knowledge Store" 
      />
    </div>
  );
};

const RetrievalPipeline = ({ onLlamaClick }) => {
  const paths = [
    { d: calculatePath(RET.col_query + R.md, RET.row_main, RET.col_vec - R.md, RET.row_main), color: "#f97316" }, // orange
    { d: calculatePath(RET.col_vec + R.md, RET.row_main, RET.col_ret - R.md, RET.row_main), color: "#0ea5e9", delay: 0.8 }, // sky
    { d: calculatePath(RET.col_ret + R.md, RET.row_main, RET.col_topk - R.sm, RET.row_main), color: "#3b82f6", delay: 1.6 }, // blue
    { d: calculatePath(RET.col_topk + R.sm, RET.row_main, RET.col_llm - R.md, RET.row_top), color: "#eab308", delay: 2.4 }, // yellow
    { d: calculatePath(RET.col_topk + R.sm, RET.row_main, RET.col_llm - R.md, RET.row_bot), color: "#22c55e", delay: 2.4 }, // green
    { d: calculatePath(RET.col_llm + R.md, RET.row_top, RET.col_resp - R.lg, RET.row_main), color: "#eab308", delay: 3.5 }, // yellow
    { d: calculatePath(RET.col_llm + R.md, RET.row_bot, RET.col_resp - R.lg, RET.row_main), color: "#22c55e", delay: 3.5 }, // green
  ];

  return (
    <div className="relative w-[1200px] h-[400px] 
      bg-white/60 dark:bg-slate-800/40 
      rounded-3xl 
      border border-slate-200 dark:border-slate-700 
      overflow-hidden
      shadow-sm dark:shadow-none"
    >
      <div className="absolute top-4 left-6 text-sm font-bold 
        text-slate-500 dark:text-slate-400 
        tracking-widest uppercase"
      >
        Pipeline: Retrieval & Generation
      </div>
      
      <ConnectionLayer width={LAYOUT.ret_w} height={LAYOUT.ret_h} paths={paths} idPrefix="ret" />

      {/* Nodes */}
      <Node x={RET.col_query} y={RET.row_main} size="md" color="orange" icon={User} label="User Query" 
        tooltip="Natural Language Input" 
      />
      <Node x={RET.col_vec} y={RET.row_main} size="md" color="sky" label="Vector" sublabel="Embedding"
        tooltip="Query Projection to Vector Space" 
      >
        <div className="font-mono text-[9px]">[0.1, ...]</div>
      </Node>
      <Node x={RET.col_ret} y={RET.row_main} size="md" color="blue" icon={Search} label="Retrieval" 
        tooltip="Semantic Similarity Search (ANN)" 
      />
      <Node x={RET.col_topk} y={RET.row_main} size="sm" color="teal" icon={Layers} label="Top-K" sublabel="Chunks" 
        tooltip="Most Relevant Context Retrieval" 
      />
      <Node x={RET.col_llm} y={RET.row_top} size="md" color="yellow" label="Llama 4" sublabel="Vision" onClick={onLlamaClick}
        tooltip="Visual Reasoning Engine" 
      >
        <div className="font-bold text-lg">∞</div>
      </Node>
      <Node x={RET.col_llm} y={RET.row_bot} size="md" color="green" label="Llama 3" sublabel="Text" onClick={onLlamaClick}
        tooltip="Text Generation Engine" 
      >
        <div className="font-bold text-lg">∞</div>
      </Node>
      <Node x={RET.col_resp} y={RET.row_main} size="lg" color="green" icon={Cpu} label="Response" 
        tooltip="Context-Aware AI Response" 
      />
    </div>
  );
};

// ============================================
// 5. SECTION TITLE COMPONENT
// ============================================

const SectionTitle = () => (
  <motion.div 
    className="text-center mb-8 px-4"
    initial={{ opacity: 0, y: -20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6 }}
  >
    {/* Badge */}
    <motion.div 
      className="inline-flex items-center gap-2 px-4 py-1.5 mb-4 
        bg-gradient-to-r from-blue-500/10 to-cyan-500/10 
        dark:from-blue-500/20 dark:to-cyan-500/20
        border border-blue-200 dark:border-blue-500/30
        rounded-full text-sm font-medium 
        text-blue-600 dark:text-blue-400"
      initial={{ scale: 0.9 }}
      animate={{ scale: 1 }}
      transition={{ delay: 0.2 }}
    >
      <Sparkles size={14} className="text-blue-500 dark:text-blue-400" />
      <span>Under the Hood</span>
    </motion.div>
    
    {/* Main Title */}
    <h2 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-3
      text-slate-800 dark:text-white"
    >
      System{' '}
      <span className="bg-gradient-to-r from-blue-600 via-cyan-600 to-teal-600 
        dark:from-blue-400 dark:via-cyan-400 dark:to-teal-400 
        bg-clip-text text-transparent"
      >
        Architecture
      </span>
    </h2>
    
    {/* Subtitle */}
    <p className="text-sm md:text-base text-slate-500 dark:text-slate-400 max-w-2xl mx-auto">
      See how your documents transform into intelligent, context-aware responses 
      through our{' '}
      <span className="font-semibold text-blue-600 dark:text-cyan-400">
        Multi-Modal RAG Pipeline
      </span>
    </p>
    
    {/* Animated line */}
    <motion.div 
      className="mt-6 mx-auto h-1 rounded-full bg-gradient-to-r from-transparent via-blue-500 to-transparent"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: '120px', opacity: 1 }}
      transition={{ delay: 0.4, duration: 0.6 }}
    />
  </motion.div>
);

// ============================================
// 6. MAIN COMPONENT (RESPONSIVE + THEME SUPPORT)
// ============================================

const RAGPipeline = ({ onLlamaClick }) => {
  return (
    <motion.div 
      className="w-full py-8 md:py-12"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Outer Frame Container */}
      <div className="max-w-7xl mx-auto px-4 md:px-6">
        <div className="
          relative
          bg-gradient-to-b from-slate-50 to-white 
          dark:from-slate-900 dark:to-slate-800
          rounded-3xl md:rounded-[2rem]
          border border-slate-200 dark:border-slate-700
          shadow-xl shadow-slate-200/50 dark:shadow-black/30
          overflow-hidden
        ">
          {/* Background Decorations */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {/* Top-left glow */}
            <div className="absolute -top-40 -left-40 w-80 h-80 
              bg-blue-400/20 dark:bg-blue-500/10 
              rounded-full blur-3xl" 
            />
            {/* Bottom-right glow */}
            <div className="absolute -bottom-40 -right-40 w-80 h-80 
              bg-cyan-400/20 dark:bg-cyan-500/10 
              rounded-full blur-3xl" 
            />
            {/* Grid pattern */}
            <div className="absolute inset-0 
              opacity-[0.03] dark:opacity-[0.05] /* จางมากๆ เพื่อไม่กวน */
              bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)]
              bg-[size:24px_24px]"
            />
          </div>
          
          {/* Content */}
          <div className="relative z-10 py-8 md:py-12">
            {/* Section Title */}
            <SectionTitle />
            
            {/* Mobile Hint */}
            <MobileHint />
            
            {/* Scrollable Pipeline Container with Mobile Scale */}
            <div className="w-full overflow-x-auto pb-4
              scrollbar-hide 
              [&::-webkit-scrollbar]:hidden 
              [-ms-overflow-style:none] 
              [scrollbar-width:none]"
            >
              {/* 
                Mobile: Scale down to 55% for better viewing
                Desktop: Normal size
                Height adjustment: 55% of original (~900px total) = ~500px on mobile
              */}
              <div className="
                origin-top-left
                scale-[0.55] md:scale-100
                w-[1200px] md:w-auto
                h-[650px] md:h-auto
                md:min-w-[1200px]
              ">
                <div className="flex flex-col items-center gap-8 px-4">
                  <IndexingPipeline onLlamaClick={onLlamaClick} />
                  <RetrievalPipeline onLlamaClick={onLlamaClick} />
                </div>
              </div>
            </div>
            
            {/* Legend */}
            <motion.div 
              className="flex flex-wrap justify-center gap-3 md:gap-5 mt-8 px-4 
                text-[10px] md:text-xs text-slate-600 dark:text-slate-400"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded bg-red-500/60" />
                <span>Input</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded bg-sky-500/60" />
                <span>Text Processing</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded bg-yellow-500/60" />
                <span>Vision Model</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded bg-green-500/60" />
                <span>Language Model</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded bg-blue-500/60" />
                <span>Vector Storage</span>
              </div>
              <div className="flex items-center gap-1.5">
                <motion.div 
                  className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full 
                    bg-white dark:bg-cyan-400 
                    border border-slate-300 dark:border-transparent"
                  animate={{ 
                    boxShadow: ['0 0 4px #06b6d4', '0 0 12px #06b6d4', '0 0 4px #06b6d4'],
                  }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <span>Data Flow</span>
              </div>
            </motion.div>
            
            {/* Powered by badge */}
            <motion.div 
              className="flex justify-center mt-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 
                bg-slate-100 dark:bg-slate-800/60 
                rounded-full text-xs 
                text-slate-500 dark:text-slate-400
                border border-slate-200 dark:border-slate-700"
              >
                <Zap size={12} className="text-yellow-500" />
                <span>Powered by</span>
                <span className="font-bold text-slate-700 dark:text-slate-200">Llama 3 & 4</span>
                <span className="text-slate-400 dark:text-slate-500">+</span>
                <span className="font-bold text-slate-700 dark:text-slate-200">ChromaDB</span>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default RAGPipeline;
