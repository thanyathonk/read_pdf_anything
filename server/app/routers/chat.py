from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.dependencies import get_user_id_from_token

router = APIRouter()


@router.post("/pdf", response_model=ChatResponse)
async def chat_with_pdf(
    request: ChatRequest,
    user_id: Optional[str] = Depends(get_user_id_from_token),
):
    """Chat with PDF using RAG"""
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message is required")

        if not request.pdfIds or len(request.pdfIds) == 0:
            raise HTTPException(
                status_code=400, detail="At least one PDF must be selected to chat"
            )

        pdf_ids = request.pdfIds

        # Convert chat history to list of dicts
        chat_history = []
        if request.chatHistory and len(request.chatHistory) > 0:
            chat_history = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in request.chatHistory
            ]

        result = await rag_service.chat_with_pdf(
            request.message, pdf_ids, chat_history=chat_history, user_id=user_id
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Failed to process chat request"),
            )

        from app.models.schemas import SourceInfo

        sources = [SourceInfo(**source) for source in result["sources"]]

        return ChatResponse(success=True, response=result["response"], sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("Chat with PDF error")
        raise HTTPException(
            status_code=500, detail="Failed to process your request. Please try again."
        )
