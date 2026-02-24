from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pdf, chat, auth
from app.services.database import database
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Connect to MongoDB (similar to await connectDB())
    from app.services.database import connect_db
    await connect_db()
    yield
    # Shutdown
    await database.disconnect()

app = FastAPI(
    title="ReadPDF AI API",
    description="RAG API for PDF documents using LangChain and FAISS",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(auth.router)

@app.get("/")
async def root():
    return {
        "success": True,
        "message": "ReadPDF AI Server is Running",
        "version": "1.0.0",
        "database_connected": database.is_connected,
        "endpoints": {
            "pdf": "/api/pdf",
            "chat": "/api/chat",
            "auth": "/api/auth"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected" if database.is_connected else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )

