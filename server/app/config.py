import logging
import os
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)

# Default JWT secret - MUST be overridden in production via JWT_SECRET env var
_DEFAULT_JWT_SECRET = "your-super-secret-key-change-in-production"


class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    DEBUG: bool = True

    # API Keys
    GROQ_API_KEY: Optional[str] = None

    # MongoDB
    # For MongoDB Atlas: mongodb+srv://username:password@cluster.mongodb.net
    # For local MongoDB: mongodb://localhost:27017
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pdf_chat_app"

    # JWT Authentication - MUST set JWT_SECRET in production!
    JWT_SECRET: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/google/callback"

    # Gmail API
    GMAIL_API_ENABLED: bool = True

    # Groq Model Settings
    # Vision model for image analysis (must support multimodal)
    GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    # Text model for final synthesis
    GROQ_SYNTHESIS_MODEL: str = "llama-3.3-70b-versatile"

    # Ollama Settings (Primary Embeddings)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "qwen3-embedding:8b"
    USE_OLLAMA_EMBEDDINGS: bool = True  # Using Ollama embeddings (no CLIP)

    # PDF Processing (Unstructured Library)
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB (default)
    MAX_FILE_SIZE_MB: int = 10  # Maximum file size in MB
    CHUNK_SIZE: int = 10000
    CHUNK_OVERLAP: int = 1000

    # Unstructured PDF Settings
    USE_UNSTRUCTURED: bool = True  # Use unstructured library for better extraction
    UNSTRUCTURED_STRATEGY: str = "hi_res"  # "fast" (no images/tables), "hi_res" (🎯 accurate with images/tables), "ocr_only" (scanned PDFs)
    UNSTRUCTURED_CHUNKING_STRATEGY: str = "by_title"  # "by_title" or "basic"
    UNSTRUCTURED_MAX_CHARACTERS: int = 10000
    UNSTRUCTURED_NEW_AFTER_N_CHARS: int = 6000
    UNSTRUCTURED_COMBINE_TEXT_UNDER_N_CHARS: int = 2000

    # Image Processing
    IMAGE_PROMPT_TEMPLATE: str = """Analyze this image from a PDF document and provide a detailed description.

Focus on:
1. What type of visual is this? (chart, graph, table, diagram, illustration, photo, etc.)
2. Key elements: labels, titles, legends, axes, data points, text
3. Main information or insight conveyed
4. Any specific numbers, values, or data shown
5. Relationships or trends visible

Provide a comprehensive description that would help answer questions about this image."""

    # RAG Settings
    TOP_K_CHUNKS: int = 8
    PERSIST_DIRECTORY: str = "./chroma_db_storage"
    IMAGE_STORE_PATH: str = "./image_data_store.json"

    # Chat History & Context Window Settings
    MAX_CONTEXT_MESSAGES: int = 10  # Maximum messages to keep in context
    MAX_CONTEXT_TOKENS: int = 4000  # Approximate token limit for context window
    SUMMARIZE_THRESHOLD: int = 8  # Summarize when message count exceeds this

    # Device
    DEVICE: str = "cuda" if os.getenv("CUDA_AVAILABLE") == "true" else "cpu"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()

# Warn if using default JWT secret (security risk in production)
if settings.JWT_SECRET == _DEFAULT_JWT_SECRET and not settings.DEBUG:
    logger.warning(
        "SECURITY: Using default JWT_SECRET. Set JWT_SECRET in environment for production!"
    )
elif settings.JWT_SECRET == _DEFAULT_JWT_SECRET:
    logger.info(
        "Using default JWT_SECRET (dev mode). Set JWT_SECRET in .env for production."
    )
