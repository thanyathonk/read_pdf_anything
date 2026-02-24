from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from app.services.vector_store import vector_store
from app.services.pdf_service import pdf_service
from app.services.llm_service import llm_service
from app.config import settings


class RAGService:
    async def summarize_conversation(self, messages: List[Dict]) -> str:
        """Summarize conversation history when context window is full"""
        try:
            # Build conversation text
            conversation_text = "\n".join(
                [
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
                    for msg in messages
                ]
            )

            summary_prompt = f"""Summarize the following conversation about PDF documents. 
Focus on key questions asked, main topics discussed, and important information extracted.

CONVERSATION:
{conversation_text}

Provide a concise summary that captures the essential context:"""

            summary = await llm_service.synthesize_answer(summary_prompt)
            return summary
        except Exception as e:
            print(f"Error summarizing conversation: {e}")
            return "Previous conversation context"

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    def _manage_context_window(
        self, chat_history: List[Dict], current_message: str
    ) -> tuple:
        """Manage context window - return trimmed history and whether summarization is needed"""
        if not chat_history:
            return [], False

        # Estimate tokens
        total_tokens = sum(
            self._estimate_tokens(msg.get("content", "")) for msg in chat_history
        )
        total_tokens += self._estimate_tokens(current_message)

        # Check if we need to summarize
        needs_summarization = (
            len(chat_history) >= settings.SUMMARIZE_THRESHOLD
            or total_tokens > settings.MAX_CONTEXT_TOKENS
        )

        if needs_summarization:
            # Keep only recent messages (last MAX_CONTEXT_MESSAGES)
            recent_messages = chat_history[-settings.MAX_CONTEXT_MESSAGES :]
            return recent_messages, True

        # Keep all messages if within limits
        return chat_history, False

    def _is_image_related_query(self, query: str) -> bool:
        """Check if query is related to images/visual content using keywords (fallback)"""
        query_lower = query.lower()

        # Direct image keywords
        direct_image_keywords = [
            "image",
            "images",
            "picture",
            "pictures",
            "photo",
            "photos",
            "chart",
            "charts",
            "graph",
            "graphs",
            "diagram",
            "diagrams",
            "figure",
            "figures",
            "visual",
            "visualization",
            "plot",
            "plots",
            "illustration",
            "illustrations",
            "drawing",
            "drawings",
            "show",
            "display",
            "see",
            "look",
            "appear",
            "depict",
            "depicts",
            "what does",
            "describe the",
            "explain the image",
            "what is shown",
            "what is in the",
            "analyze the image",
            "what can you see",
        ]

        # Indirect image keywords - questions that likely need visual data
        indirect_image_keywords = [
            "how many",
            "how much",
            "what color",
            "what colors",
            "color represent",
            "classify",
            "classified",
            "classes",
            "category",
            "categories",
            "boundary",
            "boundaries",
            "level",
            "levels",
            "score",
            "scores",
            "value",
            "values",
            "data point",
            "data points",
            "legend",
            "axis",
            "axes",
            "label",
            "labels",
            "bar",
            "bars",
            "line",
            "lines",
            "compare",
            "comparison",
            "trend",
            "trends",
            "pattern",
            "patterns",
        ]

        # Check for direct image keywords
        if any(keyword in query_lower for keyword in direct_image_keywords):
            return True

        # Check for indirect image keywords (questions about visual data)
        if any(keyword in query_lower for keyword in indirect_image_keywords):
            return True

        return False

    def _check_image_relevance_with_semantics(
        self, query: str, image_summaries: Dict[str, str], threshold: float = 0.25
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """
        Check if query is semantically related to image summaries.
        Note: With Ollama embeddings (text-only), we rely on keyword matching.
        Returns: (should_analyze, relevant_image_ids, similarity_scores)
        """
        try:
            if not image_summaries:
                return False, [], {}

            # With Ollama (text-only embeddings), use keyword matching
            # This is a simplified fallback since we don't have image-text alignment
            query_lower = query.lower()
            relevant_images = []
            similarities = {}

            for img_id, summary in image_summaries.items():
                summary_lower = summary.lower()

                # Simple keyword overlap score
                query_words = set(query_lower.split())
                summary_words = set(summary_lower.split())
                overlap = len(query_words & summary_words)
                score = overlap / max(len(query_words), 1) if query_words else 0.0

                similarities[img_id] = score

                if score >= 0.2:  # Adjusted threshold for keyword matching
                    relevant_images.append(img_id)

            should_analyze = len(relevant_images) > 0

            return should_analyze, relevant_images, similarities

        except Exception as e:
            print(f"Error in relevance check: {e}")
            return False, [], {}

    def _is_likely_general_question(self, query: str) -> bool:
        """Fast heuristic for obvious general questions (avoids extra LLM call)"""
        q = query.strip().lower()
        if not q:
            return True
        prefixes = (
            "what is ",
            "what are ",
            "who is ",
            "who are ",
            "when did ",
            "when was ",
            "where is ",
            "where are ",
            "how does ",
            "how do ",
            "how can ",
            "how would ",
            "why does ",
            "why do ",
            "why is ",
            "define ",
            "explain ",
            "describe ",
        )
        return any(q.startswith(p) for p in prefixes)

    async def _answer_general_question(
        self, message: str, chat_history: List[Dict] = None
    ) -> Dict:
        """Answer general knowledge questions without PDF context"""
        chat_history = chat_history or []
        trimmed_history, needs_summarization = self._manage_context_window(
            chat_history, message
        )
        conversation_context = ""
        summary_context = ""
        if trimmed_history:
            if (
                needs_summarization
                and len(trimmed_history) > settings.MAX_CONTEXT_MESSAGES // 2
            ):
                older = trimmed_history[: -settings.MAX_CONTEXT_MESSAGES // 2]
                summary = await self.summarize_conversation(older)
                summary_context = f"\n\nPREVIOUS CONVERSATION SUMMARY:\n{summary}\n"
                recent_messages = trimmed_history[-settings.MAX_CONTEXT_MESSAGES // 2 :]
            else:
                recent_messages = trimmed_history
            if recent_messages:
                conversation_context = "\n\nRECENT CONVERSATION:\n"
                for msg in recent_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    conversation_context += f"{role.upper()}: {content}\n"
        general_prompt = f"""You are a helpful AI assistant. Answer the following question based on your general knowledge.

{summary_context}{conversation_context}
QUESTION: {message}

Provide a clear, accurate answer based on your knowledge:"""
        final_response = await llm_service.synthesize_answer(general_prompt)
        return {
            "success": True,
            "response": final_response,
            "sources": [],
            "mode": "general",
        }

    async def _is_general_question(self, query: str, retrieved_docs: List) -> bool:
        """Check if query is a general question that doesn't need PDF context using LLM and semantic similarity"""

        # If no retrieved docs, use LLM to determine if it's a general question
        if not retrieved_docs or len(retrieved_docs) == 0:
            decision_prompt = f"""Determine if the following question is a general knowledge question that can be answered without specific document context, or if it requires information from a specific document/paper.

Question: "{query}"

Answer with ONLY "GENERAL" if it's a general knowledge question that can be answered from common knowledge (e.g., "What is machine learning?", "How does photosynthesis work?", "What is the capital of France?").
Answer with ONLY "DOCUMENT" if it requires specific document context or information from a particular study/paper (e.g., "What method did the authors use?", "What are the results?", "How many participants were there?").

Answer:"""

            try:
                decision = await llm_service.synthesize_answer(decision_prompt)
                decision_clean = decision.strip().upper()
                is_general = (
                    "GENERAL" in decision_clean and "DOCUMENT" not in decision_clean
                )
                print(
                    f"[General Question Check] LLM decision (no docs): {decision_clean} -> Is general: {is_general}"
                )
                return is_general
            except Exception as e:
                print(f"Warning: Failed to check if general question: {e}")
                # Fallback: assume it's a general question if no docs retrieved
                return True

        # If we have retrieved docs, use LLM to check relevance (accurate)

        # Method 2: Use LLM to check if retrieved content is relevant to the question
        # This is more accurate than keyword matching and works for any question type
        retrieved_content = " ".join(
            [doc.page_content[:200] for doc, _ in retrieved_docs[:3]]
        )

        relevance_prompt = f"""Determine if the following retrieved content from a document is relevant to answering the question.

Question: "{query}"

Retrieved content (first 200 chars from top 3 results):
{retrieved_content[:500]}

Answer with ONLY "RELEVANT" if the content is relevant and can help answer the question.
Answer with ONLY "NOT_RELEVANT" if the content is not relevant (meaning the question is likely a general knowledge question that doesn't need this document).

Answer:"""

        try:
            relevance_decision = await llm_service.synthesize_answer(relevance_prompt)
            relevance_clean = relevance_decision.strip().upper()
            is_not_relevant = "NOT_RELEVANT" in relevance_clean
            print(
                f"[General Question Check] LLM relevance check: {relevance_clean} -> Is general: {is_not_relevant}"
            )
            return is_not_relevant
        except Exception as e:
            print(f"Warning: Failed to check relevance: {e}")
            # Fallback: if similarity is available, use it
            # If similarity is medium/low, assume general question
            if "max_similarity" in locals() and max_similarity < 0.25:
                return True
            # Otherwise, assume it's not a general question (safer default)
            return False

    async def chat_with_pdf(
        self,
        message: str,
        pdf_ids: List[str],
        chat_history: List[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """Hybrid RAG: Chat with PDF using text and image analysis"""

        # Use new multi-modal RAG if unstructured is enabled
        if settings.USE_UNSTRUCTURED:
            return await self._chat_with_pdf_multimodal(
                message, pdf_ids, chat_history, user_id
            )
        else:
            return await self._chat_with_pdf_legacy(
                message, pdf_ids, chat_history, user_id
            )

    async def _chat_with_pdf_multimodal(
        self,
        message: str,
        pdf_ids: List[str],
        chat_history: List[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """New multi-modal RAG with smart routing (unstructured-based)"""
        try:
            from app.services.multimodal_rag_service import multimodal_rag_service

            # Validate PDFs
            for pdf_id in pdf_ids:
                pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                if not pdf:
                    raise ValueError(f"PDF {pdf_id} not found")

            # Fast heuristic: obvious general questions (reduces LLM calls)
            if self._is_likely_general_question(message):
                return await self._answer_general_question(message, chat_history)

            # Get sample docs for general question detection
            all_retrieved_docs = []
            for pdf_id in pdf_ids:
                try:
                    docs = vector_store.similarity_search(
                        pdf_id, message, k=3, user_id=user_id
                    )
                    all_retrieved_docs.extend([(doc, pdf_id) for doc in docs])
                except Exception:
                    pass

            # Check if general question (needs PDF context or not)
            is_general = await self._is_general_question(message, all_retrieved_docs)

            if is_general:
                print(f"[General Question] Answering directly without PDF context")

                # Build conversation context
                chat_history = chat_history or []
                trimmed_history, needs_summarization = self._manage_context_window(
                    chat_history, message
                )

                conversation_context = ""
                summary_context = ""

                if trimmed_history:
                    if (
                        needs_summarization
                        and len(trimmed_history) > settings.MAX_CONTEXT_MESSAGES // 2
                    ):
                        older_messages = trimmed_history[
                            : -settings.MAX_CONTEXT_MESSAGES // 2
                        ]
                        summary = await self.summarize_conversation(older_messages)
                        summary_context = (
                            f"\n\nPREVIOUS CONVERSATION SUMMARY:\n{summary}\n"
                        )
                        recent_messages = trimmed_history[
                            -settings.MAX_CONTEXT_MESSAGES // 2 :
                        ]
                    else:
                        recent_messages = trimmed_history

                    if recent_messages:
                        conversation_context = "\n\nRECENT CONVERSATION:\n"
                        for msg in recent_messages:
                            role = msg.get("role", "user")
                            content = msg.get("content", "")
                            conversation_context += f"{role.upper()}: {content}\n"

                # Answer general question
                general_prompt = f"""You are a helpful AI assistant. Answer the following question based on your general knowledge.

{summary_context}{conversation_context}
QUESTION: {message}

Provide a clear, accurate answer based on your knowledge:"""

                final_response = await llm_service.synthesize_answer(general_prompt)

                return {
                    "success": True,
                    "response": final_response,
                    "sources": [],
                    "mode": "general",
                }

            # Use multi-modal RAG service
            result = await multimodal_rag_service.multimodal_rag_answer(
                query=message,
                pdf_ids=pdf_ids,
                user_id=user_id,
                top_k=settings.TOP_K_CHUNKS,
            )

            return result

        except Exception as e:
            raise Exception(f"Multi-modal RAG chat failed: {str(e)}")

    async def _chat_with_pdf_legacy(
        self,
        message: str,
        pdf_ids: List[str],
        chat_history: List[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """Legacy RAG method (original implementation)"""
        try:
            # Validate PDFs - user_id is passed from endpoint (None for guest users)
            pdfs_info = []
            for pdf_id in pdf_ids:
                pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                if not pdf:
                    raise ValueError(f"PDF {pdf_id} not found")
                pdfs_info.append(pdf)

            # Get image stores for all PDFs
            all_image_stores = {}
            for pdf_id in pdf_ids:
                image_store = pdf_service.get_image_store(pdf_id)
                all_image_stores[pdf_id] = image_store

            # Check if query is image-related
            is_image_query = self._is_image_related_query(message)

            # Retrieve documents from all PDFs (for similarity check)
            text_contexts = []
            image_insights = []
            processed_images: Set[str] = set()
            target_pages: Set[int] = set()
            all_retrieved_docs = []  # Store all docs for analysis

            # Step 1: Retrieve documents from all PDFs
            for pdf_id in pdf_ids:
                # Get retriever with user_id
                retriever = vector_store.get_retriever(
                    pdf_id, k=settings.TOP_K_CHUNKS, user_id=user_id
                )
                docs = retriever.invoke(message)
                all_retrieved_docs.extend([(doc, pdf_id) for doc in docs])

            # Check if this is a general question that doesn't need PDF context
            is_general_question = await self._is_general_question(
                message, all_retrieved_docs
            )

            if is_general_question:
                print(
                    f"[General Question] Query appears to be a general question. Answering directly without PDF context."
                )

                # Manage context window for chat history
                chat_history = chat_history or []
                trimmed_history, needs_summarization = self._manage_context_window(
                    chat_history, message
                )

                # Build conversation context
                conversation_context = ""
                summary_context = ""

                if trimmed_history:
                    if (
                        needs_summarization
                        and len(trimmed_history) > settings.MAX_CONTEXT_MESSAGES // 2
                    ):
                        # Summarize older messages
                        older_messages = trimmed_history[
                            : -settings.MAX_CONTEXT_MESSAGES // 2
                        ]
                        summary = await self.summarize_conversation(older_messages)
                        summary_context = (
                            f"\n\nPREVIOUS CONVERSATION SUMMARY:\n{summary}\n"
                        )
                        recent_messages = trimmed_history[
                            -settings.MAX_CONTEXT_MESSAGES // 2 :
                        ]
                    else:
                        recent_messages = trimmed_history

                    # Build recent conversation context
                    if recent_messages:
                        conversation_context = "\n\nRECENT CONVERSATION:\n"
                        for msg in recent_messages:
                            role = msg.get("role", "user")
                            content = msg.get("content", "")
                            conversation_context += f"{role.upper()}: {content}\n"

                # Construct prompt for general question
                general_prompt = f"""You are a helpful AI assistant. Answer the following question based on your general knowledge.

{summary_context}{conversation_context}
QUESTION: {message}

Provide a clear, accurate answer based on your knowledge:"""

                # Generate answer directly without PDF context
                final_response = await llm_service.synthesize_answer(general_prompt)

                # Return empty sources for general questions
                sources = []

                return {"success": True, "response": final_response, "sources": sources}

            # Step 2: Check if top-k retrieval contains images and their summaries
            image_docs_in_topk = []
            image_summaries = {}  # Store image summaries for relevance checking

            for doc, pdf_id in all_retrieved_docs:
                if doc.metadata.get("type") == "image":
                    image_docs_in_topk.append((doc, pdf_id))
                    img_id = doc.metadata.get("image_id")
                    # Extract summary from image document content (caption/description)
                    if img_id and doc.page_content:
                        # Image documents contain: "Image ID: {img_id}\nDescription: {caption}"
                        # Extract description part for better matching
                        if "Description:" in doc.page_content:
                            description = doc.page_content.split("Description:")[
                                1
                            ].strip()
                            image_summaries[img_id] = description.lower()
                        else:
                            image_summaries[img_id] = doc.page_content.lower()

            has_images_in_topk = len(image_docs_in_topk) > 0

            # Step 3: Enhanced decision using semantic similarity
            # 1. If query has image keywords → analyze images (fast path)
            # 2. Otherwise, use semantic similarity between query and image summaries
            # 3. If similarity is high → analyze images
            should_analyze_images = False
            relevant_image_ids = []
            image_similarities = {}

            if has_images_in_topk:
                if is_image_query:
                    # Fast path: query explicitly mentions images
                    should_analyze_images = True
                    relevant_image_ids = list(image_summaries.keys())
                    print(
                        f"[Image Priority] Query is image-related. Found {len(image_docs_in_topk)} image(s) in top-{settings.TOP_K_CHUNKS} retrieval."
                    )
                else:
                    # Use semantic similarity to check if query matches image summaries
                    should_analyze, relevant_ids, similarities = (
                        self._check_image_relevance_with_semantics(
                            message,
                            image_summaries,
                            threshold=0.25,  # Adjustable threshold
                        )
                    )

                    if should_analyze:
                        should_analyze_images = True
                        relevant_image_ids = relevant_ids
                        image_similarities = similarities
                        print(
                            f"[Image Priority] Found {len(relevant_ids)} relevant image(s) based on semantic similarity. Query semantically matches image descriptions."
                        )
                        print(
                            f"   Similarity scores: {[(img_id, f'{sim:.3f}') for img_id, sim in list(similarities.items())[:3]]}"
                        )
                    else:
                        print(
                            f"[Text Priority] Images found in top-k but semantic similarity is low. Using text-based RAG."
                        )
                        if similarities:
                            print(
                                f"   Max similarity: {max(similarities.values()):.3f} (threshold: 0.25)"
                            )

            # Step 4: Process documents based on query type and retrieval results
            if should_analyze_images:
                # First, analyze images from top-k retrieval (limit to 3 most relevant)
                MAX_IMAGE_ANALYSIS = 3
                image_count = 0

                # Prioritize images by semantic similarity scores
                prioritized_image_docs = []
                other_image_docs = []

                # Sort images by similarity score (highest first)
                if image_similarities:
                    # Sort image_docs_in_topk by similarity score
                    sorted_image_docs = sorted(
                        image_docs_in_topk,
                        key=lambda x: image_similarities.get(
                            x[0].metadata.get("image_id", ""), 0.0
                        ),
                        reverse=True,
                    )
                    all_image_docs_ordered = sorted_image_docs
                else:
                    # Fallback: prioritize images that were marked as relevant
                    for doc, pdf_id in image_docs_in_topk:
                        img_id = doc.metadata.get("image_id")
                        if img_id in relevant_image_ids:
                            prioritized_image_docs.append((doc, pdf_id))
                        else:
                            other_image_docs.append((doc, pdf_id))
                    all_image_docs_ordered = prioritized_image_docs + other_image_docs

                print(
                    f"[Image Priority] Found {len(image_docs_in_topk)} image(s) in top-{settings.TOP_K_CHUNKS} retrieval. Prioritizing by semantic similarity."
                )

                for doc, pdf_id in all_image_docs_ordered:
                    if image_count >= MAX_IMAGE_ANALYSIS:
                        break

                    doc_type = doc.metadata.get("type", "text")
                    page_num = int(doc.metadata.get("page", 0))
                    doc_pdf_id = doc.metadata.get("pdf_id", pdf_id)

                    if doc_type == "image":
                        img_id = doc.metadata.get("image_id")
                        if img_id not in processed_images:
                            processed_images.add(img_id)

                            image_store = all_image_stores.get(doc_pdf_id, {})
                            if img_id in image_store:
                                img_base64 = image_store[img_id]
                                print(
                                    f"[Top-K Image] Analyzing Image {img_id} (Page {page_num})..."
                                )

                                visual_fact = (
                                    await llm_service.analyze_image_with_query(
                                        img_base64, message
                                    )
                                )

                                image_insights.append(
                                    f"- [IMAGE ANALYSIS Page {page_num} ID {img_id}]: {visual_fact}"
                                )
                                image_count += 1

                # Then, process text and table documents
                for doc, pdf_id in all_retrieved_docs:
                    doc_type = doc.metadata.get("type", "text")
                    page_num = int(doc.metadata.get("page", 0))
                    doc_pdf_id = doc.metadata.get("pdf_id", pdf_id)

                    if doc_type == "text":
                        content = doc.page_content.replace("\n", " ")
                        text_contexts.append(f"- [TEXT Page {page_num}]: {content}")
                        target_pages.add(page_num)

                    elif doc_type == "table":
                        content = doc.page_content
                        text_contexts.append(f"- [TABLE Page {page_num}]: {content}")
                        target_pages.add(page_num)

            else:
                # Text-first approach: Process text/table normally, skip image analysis
                if has_images_in_topk and not is_image_query:
                    print(
                        f"[Text Priority] Found {len(image_docs_in_topk)} image(s) in top-{settings.TOP_K_CHUNKS} retrieval, but query is not image-related. Skipping image analysis."
                    )
                else:
                    print(f"[Text Priority] Using text-based RAG...")

                for doc, pdf_id in all_retrieved_docs:
                    doc_type = doc.metadata.get("type", "text")
                    page_num = int(doc.metadata.get("page", 0))
                    doc_pdf_id = doc.metadata.get("pdf_id", pdf_id)

                    if doc_type == "text":
                        content = doc.page_content.replace("\n", " ")
                        text_contexts.append(f"- [TEXT Page {page_num}]: {content}")
                        target_pages.add(page_num)

                    elif doc_type == "table":
                        content = doc.page_content
                        text_contexts.append(f"- [TABLE Page {page_num}]: {content}")
                        target_pages.add(page_num)

                    # Skip image documents if query is not image-related
                    elif doc_type == "image" and is_image_query:
                        # Only analyze images if query is image-related
                        img_id = doc.metadata.get("image_id")
                        if img_id not in processed_images:
                            processed_images.add(img_id)

                            image_store = all_image_stores.get(doc_pdf_id, {})
                            if img_id in image_store:
                                img_base64 = image_store[img_id]
                                print(
                                    f"[Secondary Image] Analyzing Image {img_id} (Page {page_num})..."
                                )

                                visual_fact = (
                                    await llm_service.analyze_image_with_query(
                                        img_base64, message
                                    )
                                )

                                image_insights.append(
                                    f"- [IMAGE ANALYSIS Page {page_num} ID {img_id}]: {visual_fact}"
                                )

            # Smart Auto-Fetch: Only analyze additional images if query is image-related
            # This helps when text suggests looking at images but they weren't in top retrieval
            MAX_CONTEXT_AWARE_IMAGES = 2  # Limit to 2 additional images
            context_aware_count = 0

            # Only do context-aware image fetching if:
            # 1. Query is image-related
            # 2. No images were found in top-k retrieval OR we need more images
            # 3. We have text contexts suggesting pages with images
            if (
                is_image_query
                and len(target_pages) > 0
                and context_aware_count < MAX_CONTEXT_AWARE_IMAGES
            ):
                if not has_images_in_topk:
                    print(
                        f"[Context-Aware] Query is image-related. Text suggests looking at images on pages: {sorted(list(target_pages))}"
                    )
                else:
                    print(
                        f"[Context-Aware] Analyzing additional images on relevant pages..."
                    )

                # Prioritize pages that have text matches (exact pages first)
                exact_pages = set()
                for doc, pdf_id in all_retrieved_docs:
                    if doc.metadata.get("type") in ["text", "table"]:
                        exact_pages.add(int(doc.metadata.get("page", 0)))

                # Sort target pages: exact matches first
                prioritized_pages = sorted(list(exact_pages))

                for pdf_id, image_store in all_image_stores.items():
                    if context_aware_count >= MAX_CONTEXT_AWARE_IMAGES:
                        break

                    for img_id, img_base64 in image_store.items():
                        if context_aware_count >= MAX_CONTEXT_AWARE_IMAGES:
                            break

                        try:
                            # Extract page number from image ID (e.g., page_50_img_1)
                            parts = img_id.split("_")
                            if len(parts) >= 2:
                                p_num = int(parts[1])

                                # Only analyze images on exact text match pages and if not already processed
                                if (
                                    p_num in exact_pages
                                    and img_id not in processed_images
                                ):
                                    print(
                                        f"[Context-Aware] Analyzing Image {img_id} (Page {p_num})..."
                                    )

                                    visual_fact = (
                                        await llm_service.analyze_image_with_query(
                                            img_base64, message
                                        )
                                    )

                                    image_insights.append(
                                        f"- [IMAGE ANALYSIS Page {p_num} ID {img_id}]: {visual_fact}"
                                    )
                                    processed_images.add(img_id)
                                    context_aware_count += 1
                        except Exception as e:
                            print(f"Error processing image {img_id}: {e}")
                            continue

            # Manage context window
            chat_history = chat_history or []
            trimmed_history, needs_summarization = self._manage_context_window(
                chat_history, message
            )

            # Build conversation context
            conversation_context = ""
            summary_context = ""

            if trimmed_history:
                if (
                    needs_summarization
                    and len(trimmed_history) > settings.MAX_CONTEXT_MESSAGES // 2
                ):
                    # Summarize older messages
                    older_messages = trimmed_history[
                        : -settings.MAX_CONTEXT_MESSAGES // 2
                    ]
                    summary = await self.summarize_conversation(older_messages)
                    summary_context = f"\n\nPREVIOUS CONVERSATION SUMMARY:\n{summary}\n"
                    recent_messages = trimmed_history[
                        -settings.MAX_CONTEXT_MESSAGES // 2 :
                    ]
                else:
                    recent_messages = trimmed_history

                # Build recent conversation context
                if recent_messages:
                    conversation_context = "\n\nRECENT CONVERSATION:\n"
                    for msg in recent_messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        conversation_context += f"{role.upper()}: {content}\n"

            # Construct final prompt
            full_text_context = (
                "\n".join(text_contexts) if text_contexts else "No relevant text found."
            )
            full_image_context = (
                "\n".join(image_insights)
                if image_insights
                else "No relevant images found."
            )

            # Adjust prompt based on whether images were prioritized
            if has_images_in_topk and image_insights:
                # Image-first approach: Emphasize image analysis results
                final_prompt = f"""You are an expert research assistant. Answer the user's question based on the provided sources, with special attention to the image analysis results.

IMPORTANT: The user's question appears to be about visual content (images, charts, graphs, diagrams, etc.). The image analysis results below contain detailed information extracted from the images. Use these insights as the primary source for your answer, supplemented by any relevant text context.

CITATION FORMAT:
- Use simple superscript-style citations like [p.10] for page references
- For multiple pages, use [p.3,5,8] 
- Keep citations short and readable
- Place citations at the end of relevant sentences

WRITING RULES:
1. Write clear, professional answers in natural language
2. Prioritize information from image analysis when answering visual questions
3. Include page references [p.X] where information comes from
4. DO NOT use long technical IDs or complex reference formats
5. Structure with paragraphs or bullet points when helpful
6. If information cannot be found, state clearly
7. Consider the conversation context when answering
{summary_context}{conversation_context}
====================
IMAGE ANALYSIS RESULTS (Primary Source):
{full_image_context}

TEXT CONTEXT (Supporting Information):
{full_text_context}
====================

QUESTION: {message}

Answer with simple page citations, prioritizing the image analysis results:"""
            else:
                # Text-first approach: Standard RAG
                final_prompt = f"""You are an expert research assistant. Answer the user's question based on the provided sources and conversation context.

CITATION FORMAT:
- Use simple superscript-style citations like [p.10] for page references
- For multiple pages, use [p.3,5,8] 
- Keep citations short and readable
- Place citations at the end of relevant sentences

WRITING RULES:
1. Write clear, professional answers in natural language
2. Include page references [p.X] where information comes from
3. DO NOT use long technical IDs or complex reference formats
4. Structure with paragraphs or bullet points when helpful
5. If information cannot be found, state clearly
6. Consider the conversation context when answering
{summary_context}{conversation_context}
====================
SOURCES:
{full_text_context}

{full_image_context}
====================

QUESTION: {message}

Answer with simple page citations:"""

            # Generate final answer
            print("Synthesizing Final Answer...")
            final_response = await llm_service.synthesize_answer(final_prompt)

            # Prepare detailed sources with page numbers
            source_details = {}

            # Extract page numbers from text contexts
            for ctx in text_contexts:
                for pdf_id in pdf_ids:
                    pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                    if pdf:
                        pdf_name = pdf["filename"]
                        if pdf_id not in source_details:
                            source_details[pdf_id] = {
                                "pdfId": pdf_id,
                                "pdfName": pdf_name,
                                "pages": set(),
                                "types": set(),
                            }

                        # Extract page number from context
                        if "[TEXT Page " in ctx:
                            try:
                                page = int(ctx.split("[TEXT Page ")[1].split("]")[0])
                                source_details[pdf_id]["pages"].add(page)
                                source_details[pdf_id]["types"].add("text")
                            except:
                                pass
                        if "[TABLE Page " in ctx:
                            try:
                                page = int(ctx.split("[TABLE Page ")[1].split("]")[0])
                                source_details[pdf_id]["pages"].add(page)
                                source_details[pdf_id]["types"].add("table")
                            except:
                                pass

            # Extract page numbers from image insights
            for insight in image_insights:
                if "[IMAGE ANALYSIS Page " in insight:
                    try:
                        page = int(
                            insight.split("[IMAGE ANALYSIS Page ")[1].split(" ")[0]
                        )
                        for pdf_id in pdf_ids:
                            pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                            if pdf:
                                if pdf_id not in source_details:
                                    source_details[pdf_id] = {
                                        "pdfId": pdf_id,
                                        "pdfName": pdf["filename"],
                                        "pages": set(),
                                        "types": set(),
                                    }
                                source_details[pdf_id]["pages"].add(page)
                                source_details[pdf_id]["types"].add("image")
                    except:
                        pass

            # Convert sets to sorted lists
            sources = []
            for pdf_id, details in source_details.items():
                sources.append(
                    {
                        "pdfId": details["pdfId"],
                        "pdfName": details["pdfName"],
                        "pages": sorted(list(details["pages"])),
                        "types": list(details["types"]),
                    }
                )

            # If no sources extracted, add all PDFs
            if not sources:
                for pdf_id in pdf_ids:
                    pdf = await pdf_service.get_pdf(pdf_id, user_id=user_id)
                    sources.append(
                        {
                            "pdfId": pdf_id,
                            "pdfName": pdf["filename"] if pdf else pdf_id,
                            "pages": [],
                            "types": [],
                        }
                    )

            return {"success": True, "response": final_response, "sources": sources}

        except Exception as e:
            raise Exception(f"RAG chat failed: {str(e)}")


# Singleton instance
rag_service = RAGService()
