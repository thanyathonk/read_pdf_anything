from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional
from app.models.schemas import (
    PDFUploadResponse,
    PDFInfoResponse,
    PDFListResponse,
    PDFUpdateNameRequest,
    ErrorResponse,
)
from app.services.pdf_service import pdf_service
from app.services.database import database
from app.config import settings
from app.dependencies import get_user_id_from_token

router = APIRouter()


@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(get_user_id_from_token),
):
    """Upload and process PDF file"""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file
        pdf_bytes = await file.read()

        # Validate file size
        file_size = len(pdf_bytes)
        max_size = settings.MAX_FILE_SIZE

        if file_size > max_size:
            max_size_mb = settings.MAX_FILE_SIZE_MB
            file_size_mb = f"{file_size / (1024 * 1024):.2f}"
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size_mb}MB) exceeds maximum limit of {max_size_mb}MB. Please upload a smaller file.",
            )

        # Additional check: warn if file is very large (might take long to process)
        if file_size > max_size * 0.8:  # 80% of max size
            # Still allow but might be slow
            pass

        # Process PDF with user_id (None for guest users)
        pdf_data = await pdf_service.process_pdf(
            pdf_bytes, file.filename, user_id=user_id
        )

        return PDFUploadResponse(
            success=True,
            pdfId=pdf_data["id"],
            filename=pdf_data["filename"],
            size=pdf_data["size"],
            chunkCount=pdf_data["chunkCount"],
            message="PDF uploaded and processed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("PDF operation error")
        err_str = str(e).lower()
        if "11434" in err_str or "ollama" in err_str or "connection refused" in err_str:
            raise HTTPException(
                status_code=503,
                detail="Ollama is not running. Please start Ollama (run 'ollama serve' or open Ollama app), then try again.",
            )
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get("/all", response_model=PDFListResponse)
async def get_all_pdfs(user_id: Optional[str] = Depends(get_user_id_from_token)):
    """Get all uploaded PDFs for the current user (or guest)"""
    try:
        # Get PDFs filtered by user_id
        pdfs = await pdf_service.get_all_pdfs(user_id=user_id)
        return PDFListResponse(success=True, pdfs=pdfs, count=len(pdfs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pdf_id}", response_model=PDFInfoResponse)
async def get_pdf_info(
    pdf_id: str, user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Get PDF information"""
    try:
        pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)

        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        from app.models.schemas import PDFInfo

        return PDFInfoResponse(
            success=True,
            pdf=PDFInfo(
                id=pdf["id"],
                filename=pdf["filename"],
                size=pdf["size"],
                chunkCount=pdf["chunkCount"],
                uploadedAt=pdf["uploadedAt"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("PDF operation error")
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.patch("/{pdf_id}/name")
async def update_pdf_name(
    pdf_id: str,
    request: PDFUpdateNameRequest,
    user_id: Optional[str] = Depends(get_user_id_from_token),
):
    """Update PDF filename (authenticated users only)"""
    try:
        # Only allow authenticated users to update PDF names
        if not user_id:
            raise HTTPException(
                status_code=401, detail="Authentication required to update PDF name"
            )

        # Validate filename
        if not request.filename or not request.filename.strip():
            raise HTTPException(status_code=400, detail="Filename is required")

        updated = await pdf_service.update_pdf_name(
            pdf_id, request.filename.strip(), user_id=user_id
        )

        if not updated:
            raise HTTPException(status_code=404, detail="PDF not found")

        return {"success": True, "message": "PDF name updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("PDF operation error")
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.delete("/{pdf_id}")
async def delete_pdf(
    pdf_id: str, user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Delete PDF"""
    try:
        deleted = await pdf_service.delete_pdf(pdf_id, user_id=user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="PDF not found")

        return {"success": True, "message": "PDF deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("PDF operation error")
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )
