"""
Text Chunker - Post-processing chunking for unstructured elements

This module implements "by_title"-like chunking strategy AFTER hi_res extraction,
to control chunk explosion while maintaining multimodal pipeline quality.
"""

from typing import List, Dict
import uuid


class TextChunker:
    """
    Smart text chunking that mimics unstructured's "by_title" strategy
    but applied post-extraction for better control.
    """
    
    def __init__(
        self,
        combine_text_under_n_chars: int = 2000,
        new_after_n_chars: int = 6000,
        max_characters: int = 10000,
    ):
        """
        Args:
            combine_text_under_n_chars: Small elements below this are combined
            new_after_n_chars: Start new chunk after exceeding this
            max_characters: Hard limit for chunk size
        """
        self.combine_threshold = combine_text_under_n_chars
        self.new_chunk_threshold = new_after_n_chars
        self.max_chars = max_characters
    
    def chunk_text_elements(self, text_elements: List[Dict]) -> List[Dict]:
        """
        Chunk text elements using section-aware strategy.
        
        Strategy:
        1. Group by section_title (or page_number if no section)
        2. Combine small elements within same section
        3. Split into chunks when exceeding new_after_n_chars
        4. Hard limit at max_characters
        
        Args:
            text_elements: List of text dicts with 'content', 'page', 'element_id'
            
        Returns:
            List of chunked text dicts (fewer than input)
        """
        if not text_elements:
            return []
        
        print(f"[Chunker] Input: {len(text_elements)} text elements")
        
        # Step 1: Group by section/page
        grouped = self._group_by_section(text_elements)
        
        # Step 2: Chunk each group
        chunks = []
        for group_key, elements in grouped.items():
            group_chunks = self._chunk_group(elements, group_key)
            chunks.extend(group_chunks)
        
        print(f"[Chunker] Output: {len(chunks)} text chunks (reduced by {len(text_elements) - len(chunks)})")
        
        return chunks
    
    def _group_by_section(self, elements: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group elements by detecting section breaks (Title elements).
        
        Strategy:
        - When encountering a Title element, start a new section
        - Elements without titles are grouped by page
        
        Returns dict: {group_key: [elements]}
        """
        groups = {}
        current_section = None
        section_counter = 0
        
        for i, elem in enumerate(elements):
            # Check if this is a title/heading
            is_title = elem.get("is_title", False)
            page = elem.get("page", 0)
            
            if is_title:
                # Start new section with this title
                section_counter += 1
                section_title = elem.get("content", "")[:50]  # Use content as section name
                current_section = f"section_{section_counter}_{section_title}"
                
                # Create new group
                if current_section not in groups:
                    groups[current_section] = []
                
                # Add title to its own section
                groups[current_section].append(elem)
            else:
                # Regular text: add to current section or fallback to page-based grouping
                if current_section:
                    # Add to current section (following last title)
                    groups[current_section].append(elem)
                else:
                    # No section yet, group by page
                    page_key = f"page_{page}"
                    if page_key not in groups:
                        groups[page_key] = []
                    groups[page_key].append(elem)
        
        print(f"[Chunker] Grouped into {len(groups)} sections (detected {section_counter} titles)")
        return groups
    
    def _chunk_group(self, elements: List[Dict], group_key: str) -> List[Dict]:
        """
        Chunk elements within a single group (section/page).
        
        Strategy:
        - Respect Title elements as section markers (keep with following content)
        - Combine small elements (< combine_threshold)
        - Create new chunk when exceeding new_chunk_threshold
        - Hard split at max_characters
        """
        if not elements:
            return []
        
        chunks = []
        current_chunk = {
            "content": "",
            "page": elements[0].get("page", 0),
            "element_id": str(uuid.uuid4()),
            "type": "text",
            "source_count": 0,  # Track how many elements merged
            "has_title": False,
        }
        
        for i, elem in enumerate(elements):
            elem_text = elem.get("content", "").strip()
            if not elem_text:
                continue
            
            elem_len = len(elem_text)
            current_len = len(current_chunk["content"])
            is_title = elem.get("is_title", False)
            
            # Decision logic (mimics by_title with improvements)
            should_start_new = False
            
            # Rule 1: If current chunk is empty, add first element
            if current_len == 0:
                current_chunk["content"] = elem_text
                current_chunk["source_count"] = 1
                current_chunk["has_title"] = is_title
                continue
            
            # Rule 2: If this is a Title and current chunk is not empty, finalize current
            # (Titles should start new sections)
            if is_title and current_len > 0:
                chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = {
                    "content": elem_text,
                    "page": elem.get("page", 0),
                    "element_id": str(uuid.uuid4()),
                    "type": "text",
                    "source_count": 1,
                    "has_title": True,
                }
                continue
            
            # Rule 3: If adding this would exceed max_characters, finalize current
            if current_len + elem_len + 2 > self.max_chars:  # +2 for "\n\n"
                chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = {
                    "content": elem_text,
                    "page": elem.get("page", 0),
                    "element_id": str(uuid.uuid4()),
                    "type": "text",
                    "source_count": 1,
                    "has_title": is_title,
                }
                continue
            
            # Rule 4: If current chunk exceeds new_chunk_threshold, start new
            if current_len > self.new_chunk_threshold:
                should_start_new = True
            
            # Rule 5: If element is small (< combine_threshold), always merge
            if elem_len < self.combine_threshold:
                should_start_new = False
            
            # Rule 6: If current chunk has title and is substantial, prefer keeping together
            if current_chunk["has_title"] and current_len < self.new_chunk_threshold:
                should_start_new = False
            
            # Apply decision
            if should_start_new:
                # Finalize current and start new
                chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = {
                    "content": elem_text,
                    "page": elem.get("page", 0),
                    "element_id": str(uuid.uuid4()),
                    "type": "text",
                    "source_count": 1,
                    "has_title": is_title,
                }
            else:
                # Merge into current chunk
                current_chunk["content"] += "\n\n" + elem_text
                current_chunk["source_count"] += 1
                if is_title:
                    current_chunk["has_title"] = True
        
        # Don't forget the last chunk
        if current_chunk["content"]:
            chunks.append(self._finalize_chunk(current_chunk))
        
        return chunks
    
    def _finalize_chunk(self, chunk: Dict) -> Dict:
        """Add final metadata to chunk."""
        return {
            "element_id": chunk["element_id"],
            "content": chunk["content"],
            "page": chunk["page"],
            "type": "text",
            "chunk_size": len(chunk["content"]),
            "merged_count": chunk["source_count"],
        }


# Singleton instance with default params
text_chunker = TextChunker(
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
    max_characters=10000,
)
