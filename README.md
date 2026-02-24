# Multi-Modal RAG Chat System

ระบบ Retrieval-Augmented Generation (RAG) ที่รองรับการสนทนากับเอกสาร PDF แบบ Multi-Modal สามารถเข้าใจทั้งข้อความ ตาราง และรูปภาพภายใน PDF

## ✨ ฟีเจอร์หลัก

- 📄 **Multi-Modal PDF Processing**: ประมวลผล PDF ทั้งข้อความ ตาราง และรูปภาพ
- 🤖 **Intelligent RAG**: ใช้ Ollama embeddings และ Groq LLM สำหรับการตอบคำถามที่แม่นยำ
- 👤 **Dual User Mode**: รองรับทั้งผู้ใช้แบบ Guest และ Logged-in
- 🔐 **Authentication**: Google OAuth และ JWT สำหรับความปลอดภัย
- 🎨 **Modern UI**: หน้าเว็บที่สวยงามและใช้งานง่ายด้วย React + Tailwind CSS
- 🌓 **Light/Dark Mode**: รองรับธีมสว่างและมืด
- 📊 **Interactive Dashboard**: ดู PDF ที่อัปโหลดและประวัติการสนทนา

## 🏗️ สถาปัตยกรรมระบบ

### Backend (Python/FastAPI)
- **PDF Extraction**: Unstructured library สำหรับ hi-res extraction
- **Embeddings**: Ollama (qwen3-embedding:8b) สำหรับ vectorization
- **Vector Store**: ChromaDB สำหรับจัดเก็บและค้นหา embeddings
- **LLM**: Groq API (Llama 3.3-70B, Llama 4 Vision)
- **Database**: MongoDB Atlas สำหรับข้อมูลผู้ใช้และ metadata
- **Image Store**: In-memory store สำหรับรูปภาพ base64

### Frontend (React/Vite)
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **State Management**: Context API
- **Icons**: Lucide React
- **Markdown**: React Markdown สำหรับแสดงผล chat

### Pipeline Optimization
- **Smart Page Selector**: เลือกหน้าที่ต้อง process ด้วย hi-res อัจฉริยะ
- **Post-Processing Chunking**: จัดกลุ่ม text chunks ตาม section (15-30 chunks)
- **Selective Image Captioning**: caption เฉพาะรูปภาพที่จำเป็น
- **Two-Stage Answer Synthesis**: สังเคราะห์คำตอบเป็นภาษาธรรมชาติ

## 📦 โครงสร้างโปรเจค

```
project/
├── client/                 # React Frontend
│   ├── src/
│   │   ├── components/    # UI Components
│   │   ├── context/       # State Management
│   │   ├── pages/         # Page Components
│   │   ├── services/      # API Services
│   │   └── utils/         # Helper Functions
│   └── package.json
│
├── server/                # FastAPI Backend
│   ├── app/
│   │   ├── config.py     # Configuration
│   │   ├── models/       # Data Models
│   │   ├── routers/      # API Routes
│   │   └── services/     # Business Logic
│   ├── main.py           # Entry Point
│   └── requirements.txt
│
└── docs_archive/          # Documentation Archive
    ├── server_technical/  # Technical Docs
    ├── setup_guides/      # Setup Guides
    └── client_docs/       # Client Docs
```

## 🚀 เริ่มต้นใช้งาน

### 1. ติดตั้ง Dependencies

#### Backend
```bash
cd server
conda activate embedding  # หรือ virtual environment ของคุณ
pip install -r requirements.txt
```

#### Frontend
```bash
cd client
npm install
```

### 2. ตั้งค่า Environment Variables

#### Backend (.env)
```env
# MongoDB
MONGODB_URI=your_mongodb_uri

# JWT
JWT_SECRET=your_jwt_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Groq API
GROQ_API_KEY=your_groq_api_key

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
```

#### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

### 3. เริ่ม Services

#### 1) เริ่ม Ollama Server
```bash
ollama serve
ollama pull qwen3-embedding:8b
```

#### 2) เริ่ม Backend
```bash
cd server
uvicorn main:app --reload --port 8000
```

#### 3) เริ่ม Frontend
```bash
cd client
npm run dev
```

เปิดเบราว์เซอร์ที่: http://localhost:5173

## 📖 เอกสารเพิ่มเติม

- **SKILLS.md**: รายละเอียดความสามารถของระบบ
- **docs_archive/**: เอกสารทางเทคนิคและ setup guides ทั้งหมด
  - `server_technical/`: เอกสารเชิงลึกเกี่ยวกับ RAG pipeline
  - `setup_guides/`: คู่มือติดตั้งและ configuration
  - `client_docs/`: เอกสาร frontend features

## 🔧 เทคโนโลยีที่ใช้

### Backend
- Python 3.10+
- FastAPI
- Unstructured
- Ollama
- ChromaDB
- MongoDB + Motor
- Groq SDK

### Frontend
- React 18
- Vite
- Tailwind CSS
- Framer Motion
- Axios
- React Router

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

พัฒนาโดย: [Your Name]
