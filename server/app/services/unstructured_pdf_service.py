"""
Unstructured PDF Service - Optimized for Speed & Quality

Key optimizations:
1. Two-pass processing: fast scan → selective hi_res
2. Separate table HTML vs table-as-image
3. Selective image captioning (only graphs, plots, diagrams)
4. Smart chunking for better embedding efficiency
"""

from app.config import settings
from typing import Dict, List
import os
import tempfile
import time
import uuid


class ImageClassifier:
    """Classify images to determine if they need captioning."""

    # Images that typically need captioning
    CAPTION_WORTHY_PATTERNS = [
        "graph",
        "plot",
        "chart",
        "diagram",
        "figure",
        "illustration",
        "flowchart",
        "timeline",
        "map",
    ]

    @staticmethod
    def should_caption_image(element, context_text: str = "") -> bool:
        """
        Determine if an image should be sent for captioning.

        Args:
            element: Image element from unstructured
            context_text: Surrounding text context

        Returns:
            True if image should be captioned
        """
        # Always caption if we have no context
        if not context_text:
            return True

        context_lower = context_text.lower()

        # Check if context mentions visual content
        for pattern in ImageClassifier.CAPTION_WORTHY_PATTERNS:
            if pattern in context_lower:
                return True

        # Check element metadata for hints
        if hasattr(element, "metadata"):
            # If it's from a table, might be table-as-image
            if hasattr(element.metadata, "parent_id"):
                return True

        # Default: caption it (conservative approach)
        return True


class UnstructuredPDFService:
    """Service for extracting content from PDFs using unstructured library."""

    @staticmethod
    async def extract_pdf_elements(pdf_bytes: bytes, filename: str) -> Dict[str, List]:
        """
        Extract text, tables, and images from PDF with smart routing.

        Two-pass approach:
        1. Fast scan to identify pages with complex content
        2. Hi-res processing only on selected pages

        Returns:
            {
                "texts": [...],
                "tables": [...],  # Only HTML tables
                "images_base64": [...]  # Images + table-as-image
            }
        """
        try:
            from unstructured.partition.pdf import partition_pdf
            from unstructured.documents.elements import (
                Image as UnstructuredImage,
                Table,
            )
            from app.services.smart_page_selector import SmartPageSelector

            t_total = time.perf_counter()
            print(f"[Unstructured] Processing: {filename}")

            # Create temporary file from bytes
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(pdf_bytes)

            try:
                # ============================================
                # PHASE 1: Fast scan to identify complex pages
                # ============================================
                t1 = time.perf_counter()
                print(f"[Unstructured] Phase 1: Fast scan...")

                fast_elements = partition_pdf(
                    filename=tmp_path,
                    strategy="fast",
                    extract_images_in_pdf=False,  # Don't extract images in fast mode
                    infer_table_structure=False,  # Don't infer tables in fast mode
                )

                t1_elapsed = time.perf_counter() - t1
                print(
                    f"[Unstructured] Fast scan found {len(fast_elements)} text elements [{t1_elapsed:.2f}s]"
                )

                # Determine if we should use hi_res at all
                use_hires = not SmartPageSelector.should_use_hires_fallback(
                    fast_elements
                )

                if use_hires:
                    # Select pages for hi_res processing
                    hires_pages = SmartPageSelector.select_pages_for_hires(
                        fast_elements,
                        threshold=0.3,  # Configurable threshold
                        max_pages=None,  # No limit by default
                    )

                    print(
                        f"[Unstructured] Selected {len(hires_pages)} pages for hi_res: {sorted(hires_pages)}"
                    )
                else:
                    print(
                        f"[Unstructured] Document is simple/short, using hi_res for all pages"
                    )
                    hires_pages = None

                # ============================================
                # PHASE 2: Hi-res processing on selected pages
                # ============================================
                t2 = time.perf_counter()
                if hires_pages and len(hires_pages) > 0:
                    print(
                        f"[Unstructured] Phase 2: Hi-res processing on {len(hires_pages)} pages..."
                    )

                    # Process only selected pages with hi_res
                    hires_elements = partition_pdf(
                        filename=tmp_path,
                        strategy="hi_res",
                        infer_table_structure=True,
                        extract_images_in_pdf=True,
                        extract_image_block_to_payload=True,
                        pages=list(hires_pages) if hires_pages else None,
                    )

                    t2_elapsed = time.perf_counter() - t2
                    print(
                        f"[Unstructured] Hi-res extracted {len(hires_elements)} elements [{t2_elapsed:.2f}s]"
                    )

                    # Merge: use hi_res for selected pages, fast for others
                    all_elements = UnstructuredPDFService._merge_elements(
                        fast_elements, hires_elements, hires_pages
                    )
                else:
                    # Fallback: use hi_res for entire document
                    print(f"[Unstructured] Phase 2: Hi-res processing on all pages...")
                    all_elements = partition_pdf(
                        filename=tmp_path,
                        strategy="hi_res",
                        infer_table_structure=True,
                        extract_images_in_pdf=True,
                        extract_image_block_to_payload=True,
                    )
                    t2_elapsed = time.perf_counter() - t2
                    print(
                        f"[Unstructured] Hi-res extracted {len(all_elements)} elements [{t2_elapsed:.2f}s]"
                    )

                print(f"[Unstructured] Total elements: {len(all_elements)}")

                # ============================================
                # PHASE 3: Categorize and process elements
                # ============================================
                t3 = time.perf_counter()
                result = UnstructuredPDFService._categorize_elements(all_elements)
                t3_elapsed = time.perf_counter() - t3

                print(f"[Unstructured] Raw categorization [{t3_elapsed:.2f}s]:")
                print(f"  - Raw Texts: {len(result['texts'])}")
                print(f"  - Tables (HTML): {len(result['tables'])}")
                print(f"  - Images (for captioning): {len(result['images_base64'])}")

                # ============================================
                # PHASE 4: Post-processing chunking for texts
                # ============================================
                from app.services.text_chunker import text_chunker

                t4 = time.perf_counter()
                # Apply smart chunking to reduce text chunk explosion
                chunked_texts = text_chunker.chunk_text_elements(result["texts"])
                result["texts"] = chunked_texts
                t4_elapsed = time.perf_counter() - t4

                print(f"[Chunker] Completed in {t4_elapsed:.2f}s")
                print(f"[Unstructured] Final Summary:")
                print(f"  - Text Chunks: {len(result['texts'])} (after chunking)")
                print(f"  - Tables: {len(result['tables'])}")
                print(f"  - Images: {len(result['images_base64'])}")

                t_total_elapsed = time.perf_counter() - t_total
                print(
                    f"[Unstructured] Extract total: {t_total_elapsed:.2f}s (Phase1: {t1_elapsed:.2f}s, Phase2: {t2_elapsed:.2f}s, Phase3: {t3_elapsed:.2f}s, Phase4: {t4_elapsed:.2f}s)"
                )
                return result

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except ImportError:
            raise Exception(
                "unstructured library not installed. "
                "Install with: pip install unstructured[pdf]"
            )
        except Exception as e:
            raise Exception(f"Unstructured extraction failed: {str(e)}")

    @staticmethod
    def _merge_elements(
        fast_elements: list, hires_elements: list, hires_pages: set
    ) -> list:
        """
        Merge fast and hi_res elements.

        Strategy:
        - Use hi_res elements for pages in hires_pages
        - Use fast elements for all other pages
        """
        # Group elements by page
        hires_by_page = {}
        for elem in hires_elements:
            page = 0
            if hasattr(elem, "metadata") and hasattr(elem.metadata, "page_number"):
                page = elem.metadata.page_number or 0

            if page not in hires_by_page:
                hires_by_page[page] = []
            hires_by_page[page].append(elem)

        # Build final list
        merged = []
        for elem in fast_elements:
            page = 0
            if hasattr(elem, "metadata") and hasattr(elem.metadata, "page_number"):
                page = elem.metadata.page_number or 0

            # Skip if this page has hi_res version
            if page in hires_by_page:
                continue

            merged.append(elem)

        # Add all hi_res elements
        merged.extend(hires_elements)

        return merged

    @staticmethod
    def _categorize_elements(elements: list) -> Dict[str, List]:
        """
        Categorize elements into texts, tables (HTML only), and images.

        Key logic:
        - Table with HTML → tables[] (no captioning)
        - Table without HTML → images_base64[] (treat as image)
        - Image → images_base64[] (with selective captioning)
        """
        from unstructured.documents.elements import (
            Image as UnstructuredImage,
            Table,
        )

        texts = []
        tables = []  # HTML tables only
        images_base64 = []  # Images + table-as-image

        for i, element in enumerate(elements):
            # ============================================
            # 1. TABLE ELEMENTS
            # ============================================
            if isinstance(element, Table):
                # Check if table has HTML representation
                has_html = (
                    hasattr(element.metadata, "text_as_html")
                    and element.metadata.text_as_html
                )

                if has_html:
                    # TABLE WITH HTML → Store as structured table
                    tables.append(
                        {
                            "element_id": str(uuid.uuid4()),
                            "content": element.metadata.text_as_html,
                            "page": element.metadata.page_number
                            if hasattr(element.metadata, "page_number")
                            else 0,
                            "type": "table_html",
                        }
                    )
                else:
                    # TABLE WITHOUT HTML → Treat as image (table-as-image)
                    if (
                        hasattr(element.metadata, "image_base64")
                        and element.metadata.image_base64
                    ):
                        images_base64.append(
                            {
                                "element_id": str(uuid.uuid4()),
                                "base64": element.metadata.image_base64,
                                "page": element.metadata.page_number
                                if hasattr(element.metadata, "page_number")
                                else 0,
                                "type": "table_as_image",
                                "needs_captioning": True,  # Always caption table-as-image
                            }
                        )

            # ============================================
            # 2. IMAGE ELEMENTS
            # ============================================
            elif isinstance(element, UnstructuredImage):
                if (
                    hasattr(element.metadata, "image_base64")
                    and element.metadata.image_base64
                ):
                    # Get context for smart captioning
                    context_text = ""
                    if hasattr(element, "text"):
                        context_text = element.text or ""

                    # Determine if image needs captioning
                    needs_captioning = ImageClassifier.should_caption_image(
                        element, context_text
                    )

                    images_base64.append(
                        {
                            "element_id": str(uuid.uuid4()),
                            "base64": element.metadata.image_base64,
                            "page": element.metadata.page_number
                            if hasattr(element.metadata, "page_number")
                            else 0,
                            "type": "image",
                            "needs_captioning": needs_captioning,
                            "context": context_text[:200]
                            if context_text
                            else "",  # Store short context
                        }
                    )

            # ============================================
            # 3. TEXT ELEMENTS
            # ============================================
            elif hasattr(element, "text") and element.text:
                text_content = element.text.strip()

                # Skip very short text fragments
                if len(text_content) < 20:
                    continue

                # Extract metadata for smart chunking
                metadata = {}
                if hasattr(element, "metadata"):
                    # Get element category (Title, NarrativeText, etc.)
                    if hasattr(element.metadata, "category"):
                        metadata["category"] = element.metadata.category

                    # Get parent_id for hierarchical structure
                    if hasattr(element.metadata, "parent_id"):
                        metadata["parent_id"] = element.metadata.parent_id

                    # Get filename for tracking
                    if hasattr(element.metadata, "filename"):
                        metadata["filename"] = element.metadata.filename

                # Detect if this is a title/heading (for section breaks)
                is_title = (
                    metadata.get("category") == "Title"
                    or (len(text_content) < 100 and text_content.isupper())  # Heuristic
                )

                texts.append(
                    {
                        "element_id": str(uuid.uuid4()),
                        "content": text_content,
                        "page": element.metadata.page_number
                        if hasattr(element.metadata, "page_number")
                        else 0,
                        "type": "text",
                        "category": metadata.get("category", "Text"),
                        "is_title": is_title,
                        "section_title": text_content
                        if is_title
                        else None,  # Use title as section marker
                    }
                )

        return {
            "texts": texts,
            "tables": tables,
            "images_base64": images_base64,
        }

    @staticmethod
    async def generate_image_captions(
        images_base64: List[Dict], llm_service
    ) -> List[Dict]:
        """
        Generate captions for images using vision model.

        Only generates captions for images marked with needs_captioning=True.
        This implements selective image captioning to reduce latency.

        Args:
            images_base64: List of image dicts with 'element_id', 'base64', 'needs_captioning'
            llm_service: LLM service instance

        Returns:
            List of caption dicts with 'element_id', 'content', 'page'
        """
        # Filter to only images that need captioning
        images_to_caption = [
            img
            for img in images_base64
            if img.get(
                "needs_captioning", True
            )  # Default True for backward compatibility
        ]

        t_start = time.perf_counter()
        print(
            f"[Caption] Generating captions for {len(images_to_caption)}/{len(images_base64)} images..."
        )

        if not images_to_caption:
            return []

        captions = []

        for img in images_to_caption:
            try:
                # Use vision model to generate caption
                caption_text = await llm_service.analyze_image_with_query(
                    img["base64"],
                    "Describe this image in detail, focusing on data, trends, and key insights.",
                )

                if caption_text:
                    captions.append(
                        {
                            "element_id": img["element_id"],
                            "content": f"Image caption: {caption_text}",
                            "page": img.get("page", 0),
                        }
                    )

            except Exception as e:
                print(f"[Caption] Failed to caption image {img['element_id']}: {e}")
                # Add fallback caption
                captions.append(
                    {
                        "element_id": img["element_id"],
                        "content": f"Image (type: {img.get('type', 'unknown')}, page: {img.get('page', 0)})",
                        "page": img.get("page", 0),
                    }
                )

        t_elapsed = time.perf_counter() - t_start
        print(f"[Caption] Generated {len(captions)} captions [{t_elapsed:.2f}s]")
        return captions


# Export singleton instance
unstructured_pdf_service = UnstructuredPDFService()
