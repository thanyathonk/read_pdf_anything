from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PDFUploadResponse(BaseModel):
    success: bool
    pdfId: str
    filename: str
    size: int
    chunkCount: int
    message: str


class PDFInfo(BaseModel):
    id: str
    filename: str
    size: int
    chunkCount: int
    uploadedAt: int


class PDFInfoResponse(BaseModel):
    success: bool
    pdf: PDFInfo


class PDFListResponse(BaseModel):
    success: bool
    pdfs: List[PDFInfo]
    count: int


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

    class Config:
        # Allow extra fields to be ignored
        extra = "ignore"


class ChatRequest(BaseModel):
    message: str
    pdfIds: List[str]  # Required - at least one PDF to chat
    chatHistory: Optional[List[ChatMessage]] = None  # Previous conversation messages


class SourceInfo(BaseModel):
    pdfId: str
    pdfName: str
    pages: Optional[List[int]] = []
    types: Optional[List[str]] = []


class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[SourceInfo]


class ErrorResponse(BaseModel):
    success: bool
    message: str


class GuestDataMigration(BaseModel):
    pdf_ids: List[str] = []
    chat_messages: List[dict] = []


class PDFUpdateNameRequest(BaseModel):
    filename: str
