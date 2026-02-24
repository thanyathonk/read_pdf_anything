"""
Multi-Modal RAG Service - Smart routing between text and vision models
Based on unstructured extraction with image captions
"""
from typing import List, Dict, Optional
from app.services.vector_store import vector_store
from app.services.pdf_service import pdf_service
from app.services.llm_service import llm_service
from app.services.image_store_service import image_store_service
from app.config import settings


class MultiModalRAGService:
    """
    Smart RAG with routing:
    - If image_caption found in top-k retrieval → use vision model
    - Otherwise → use text-only model
    """
    
    async def retrieve_and_route(
        self,
        query: str,
        pdf_ids: List[str],
        k: int = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """
        Retrieve documents and decide whether to use vision model
        
        Returns:
        {
            "use_vision": bool,
            "text_docs": List[Document],
            "table_docs": List[Document],
            "image_caption_docs": List[Document],
        }
        """
        k = k or settings.TOP_K_CHUNKS
        
        text_docs = []
        table_docs = []
        image_caption_docs = []
        
        # Search across all PDFs
        for pdf_id in pdf_ids:
            try:
                docs = vector_store.similarity_search(
                    pdf_id, query, k=k, user_id=user_id
                )
                
                # Separate by type
                for doc in docs:
                    doc_type = doc.metadata.get("type", "text")
                    
                    if doc_type == "image_caption":
                        image_caption_docs.append(doc)
                    elif doc_type == "table":
                        table_docs.append(doc)
                    elif doc_type == "text":
                        text_docs.append(doc)
                        
            except Exception as e:
                print(f"[Routing] Error searching PDF {pdf_id}: {e}")
                continue
        
        # Decision: use vision if we found image captions in top-k
        use_vision = len(image_caption_docs) > 0
        
        if use_vision:
            print(f"[Routing] Vision path: found {len(image_caption_docs)} image captions")
        else:
            print(f"[Routing] Text path: {len(text_docs)} texts, {len(table_docs)} tables")
        
        return {
            "use_vision": use_vision,
            "text_docs": text_docs,
            "table_docs": table_docs,
            "image_caption_docs": image_caption_docs,
        }
    
    async def fetch_images_for_vision(
        self,
        image_caption_docs: List,
        pdf_ids: List[str],
    ) -> List[Dict]:
        """
        Fetch base64 images corresponding to image captions using InMemoryStore
        
        Returns list of:
        {
            "base64": str,
            "caption": str,
            "page": int,
            "element_id": str,
        }
        """
        images = []
        
        for cap_doc in image_caption_docs:
            element_id = cap_doc.metadata.get("element_id")
            pdf_id = cap_doc.metadata.get("pdf_id")
            
            # Get image from InMemoryStore
            img_doc = image_store_service.get_image(pdf_id, element_id)
            
            if img_doc:
                images.append({
                    "base64": img_doc.page_content,
                    "caption": cap_doc.page_content,
                    "page": cap_doc.metadata.get("page", 0),
                    "element_id": element_id,
                })
        
        return images
    
    async def answer_with_vision(
        self,
        query: str,
        images: List[Dict],
        text_docs: List = None,
        table_docs: List = None,
    ) -> str:
        """
        Answer query using vision model for images.
        Synthesizes information from images, tables, and text into a natural response.
        """
        # Limit number of images to analyze (performance optimization)
        MAX_IMAGES_TO_ANALYZE = 5
        images_to_analyze = images[:MAX_IMAGES_TO_ANALYZE]
        
        if len(images) > MAX_IMAGES_TO_ANALYZE:
            print(f"[Vision] Limiting analysis to top {MAX_IMAGES_TO_ANALYZE}/{len(images)} images")
        
        # Collect image analysis results
        image_insights = []
        for img in images_to_analyze:
            try:
                print(f"[Vision] Analyzing image on page {img['page']}...")
                
                visual_answer = await llm_service.analyze_image_with_query(
                    img["base64"],
                    query
                )
                
                image_insights.append({
                    "page": img['page'],
                    "analysis": visual_answer
                })
                
            except Exception as e:
                print(f"[Vision] Error analyzing image: {e}")
                continue
        
        # Collect supporting context (text and tables)
        supporting_context = []
        
        if table_docs:
            for doc in table_docs[:2]:  # Limit to top 2
                page = doc.metadata.get("page", 0)
                content = doc.page_content
                supporting_context.append({
                    "type": "table",
                    "page": page,
                    "content": content
                })
        
        if text_docs:
            for doc in text_docs[:3]:  # Limit to top 3
                page = doc.metadata.get("page", 0)
                content = doc.page_content[:500]  # Truncate long text
                supporting_context.append({
                    "type": "text",
                    "page": page,
                    "content": content
                })
        
        # Synthesize final answer using LLM
        synthesis_prompt = self._build_vision_synthesis_prompt(
            query, image_insights, supporting_context
        )
        
        final_answer = await llm_service.synthesize_answer(synthesis_prompt)
        return final_answer
    
    def _build_vision_synthesis_prompt(
        self,
        query: str,
        image_insights: List[Dict],
        supporting_context: List[Dict]
    ) -> str:
        """Build prompt for synthesizing vision + context into natural answer."""
        
        prompt_parts = [
            "You are a helpful assistant that synthesizes information from images, tables, and text to answer questions.",
            "",
            "**Instructions:**",
            "- Provide a clear, concise answer in natural language",
            "- Synthesize information from all sources (images, tables, text)",
            "- Do NOT show raw HTML, page numbers, or context labels like [Table - Page X]",
            "- If relevant, mention the source descriptively (e.g., 'according to the table' or 'as shown in the figure')",
            "- Focus on answering the question directly",
            "",
            f"**Question:** {query}",
            ""
        ]
        
        # Add image insights
        if image_insights:
            prompt_parts.append("**Image Analysis:**")
            for i, insight in enumerate(image_insights, 1):
                prompt_parts.append(f"Image {i} (page {insight['page']}): {insight['analysis']}")
            prompt_parts.append("")
        
        # Add supporting context
        if supporting_context:
            prompt_parts.append("**Supporting Information:**")
            for ctx in supporting_context:
                if ctx['type'] == 'table':
                    prompt_parts.append(f"Table from page {ctx['page']}:")
                    prompt_parts.append(ctx['content'])
                else:
                    prompt_parts.append(f"Text from page {ctx['page']}: {ctx['content']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "**Your Answer:**",
            "(Synthesize the information above into a clear, natural answer. Do not quote raw context.)"
        ])
        
        return "\n".join(prompt_parts)
    
    async def answer_with_text_llm(
        self,
        query: str,
        text_docs: List,
        table_docs: List = None,
    ) -> str:
        """
        Answer query using text-only LLM.
        Synthesizes information from text and tables into a natural response.
        
        Note: Table HTML is prioritized over plain text for better structured data handling.
        """
        # PRIORITY 1: Collect table information (structured data is more valuable)
        tables_info = []
        if table_docs:
            print(f"[Text LLM] Using {len(table_docs)} table(s) as primary context")
            for doc in table_docs:
                page = doc.metadata.get("page", 0)
                content = doc.page_content
                tables_info.append({
                    "page": page,
                    "content": content
                })
        
        # PRIORITY 2: Collect text information
        texts_info = []
        if text_docs:
            print(f"[Text LLM] Using {len(text_docs)} text document(s) as supporting context")
            for doc in text_docs:
                page = doc.metadata.get("page", 0)
                content = doc.page_content
                texts_info.append({
                    "page": page,
                    "content": content
                })
        
        # Build synthesis prompt
        prompt = self._build_text_synthesis_prompt(query, tables_info, texts_info)
        
        response = await llm_service.synthesize_answer(prompt)
        return response
    
    def _build_text_synthesis_prompt(
        self,
        query: str,
        tables_info: List[Dict],
        texts_info: List[Dict]
    ) -> str:
        """Build prompt for synthesizing text + tables into natural answer."""
        
        prompt_parts = [
            "You are a helpful assistant that answers questions based on provided documents.",
            "",
            "**Instructions:**",
            "- Provide a clear, concise answer in natural language",
            "- Synthesize information from tables and text naturally",
            "- Do NOT show raw HTML tables, page numbers, or labels like [Table - Page X]",
            "- If you reference data, describe it naturally (e.g., 'the table shows...' or 'according to the text...')",
            "- Focus on directly answering the question",
            "- If the information is insufficient, say so clearly",
            "",
            f"**Question:** {query}",
            ""
        ]
        
        # Add tables first (priority)
        if tables_info:
            prompt_parts.append("**Tables:**")
            for i, table in enumerate(tables_info, 1):
                prompt_parts.append(f"Table {i} (from page {table['page']}):")
                prompt_parts.append(table['content'])
                prompt_parts.append("")
        
        # Add text content
        if texts_info:
            prompt_parts.append("**Text Content:**")
            for i, text in enumerate(texts_info, 1):
                prompt_parts.append(f"Excerpt {i} (from page {text['page']}):")
                prompt_parts.append(text['content'])
                prompt_parts.append("")
        
        prompt_parts.extend([
            "**Your Answer:**",
            "(Provide a natural, synthesized answer based on the information above. Do not show raw HTML or quote context verbatim.)"
        ])
        
        return "\n".join(prompt_parts)
    
    async def multimodal_rag_answer(
        self,
        query: str,
        pdf_ids: List[str],
        user_id: Optional[str] = None,
        top_k: int = None,
    ) -> Dict:
        """
        Main entry point for multi-modal RAG
        
        Returns:
        {
            "success": bool,
            "response": str,
            "sources": List[Dict],
            "mode": "vision" | "text",
        }
        """
        try:
            # Step 1: Retrieve and route
            routed = await self.retrieve_and_route(
                query, pdf_ids, k=top_k, user_id=user_id
            )
            
            # Step 2: Execute appropriate path
            if routed["use_vision"]:
                # Vision path
                images = await self.fetch_images_for_vision(
                    routed["image_caption_docs"],
                    pdf_ids
                )
                
                answer = await self.answer_with_vision(
                    query,
                    images,
                    routed["text_docs"],
                    routed["table_docs"],
                )
                
                mode = "vision"
                
            else:
                # Text path
                answer = await self.answer_with_text_llm(
                    query,
                    routed["text_docs"],
                    routed["table_docs"],
                )
                
                mode = "text"
            
            # Step 3: Prepare sources
            sources = []
            source_pages = set()
            
            # Collect page numbers from all retrieved docs
            all_docs = (
                routed["text_docs"] + 
                routed["table_docs"] + 
                routed["image_caption_docs"]
            )
            
            for doc in all_docs:
                page = doc.metadata.get("page", 0)
                pdf_id = doc.metadata.get("pdf_id")
                if page:
                    source_pages.add((pdf_id, page))
            
            # Group by PDF
            pdf_pages = {}
            for pdf_id, page in source_pages:
                if pdf_id not in pdf_pages:
                    pdf_pages[pdf_id] = []
                pdf_pages[pdf_id].append(page)
            
            # Build source info
            for pdf_id, pages in pdf_pages.items():
                pdf_info = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                if pdf_info:
                    sources.append({
                        "pdfId": pdf_id,
                        "pdfName": pdf_info.get("filename", pdf_id),
                        "pages": sorted(pages),
                        "types": [mode],
                    })
            
            return {
                "success": True,
                "response": answer,
                "sources": sources,
                "mode": mode,
            }
            
        except Exception as e:
            raise Exception(f"Multi-modal RAG failed: {str(e)}")


# Singleton instance
multimodal_rag_service = MultiModalRAGService()
