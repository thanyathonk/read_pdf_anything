"""
Smart Page Selector for Unstructured PDF Processing

This module implements intelligent page-level routing to minimize
processing time by using "fast" strategy first, then selectively
applying "hi_res" only to pages that likely contain complex elements.
"""

from typing import List, Set
import re


class SmartPageSelector:
    """
    Analyzes PDF pages to determine which ones need hi_res processing.
    """
    
    # Keywords indicating complex visual content
    TABLE_INDICATORS = [
        "table", "figure", "fig.", "chart", "graph", "diagram",
        "appendix", "supplementary", "data", "results", "method",
        "analysis", "comparison", "summary"
    ]
    
    # Patterns that suggest visual elements
    VISUAL_PATTERNS = [
        r"table\s+\d+",  # "Table 1", "Table 2"
        r"figure\s+\d+",  # "Figure 1", "Figure 2"
        r"fig\.\s*\d+",  # "Fig. 1"
        r"\(see\s+(table|figure|fig\.)",  # References to visuals
        r"as\s+shown\s+in\s+(table|figure)",
        r"illustrated\s+in",
        r"depicted\s+in",
    ]
    
    @staticmethod
    def analyze_text_for_visuals(text: str) -> float:
        """
        Analyze text content to determine likelihood of visual elements.
        
        Args:
            text: Text content from a page
            
        Returns:
            Score between 0-1 indicating likelihood of visual content
        """
        if not text or len(text.strip()) < 50:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        
        # Check for keywords (0.4 weight)
        keyword_matches = sum(
            1 for keyword in SmartPageSelector.TABLE_INDICATORS
            if keyword in text_lower
        )
        score += min(keyword_matches * 0.1, 0.4)
        
        # Check for patterns (0.6 weight)
        pattern_matches = sum(
            1 for pattern in SmartPageSelector.VISUAL_PATTERNS
            if re.search(pattern, text_lower)
        )
        score += min(pattern_matches * 0.2, 0.6)
        
        return min(score, 1.0)
    
    @staticmethod
    def select_pages_for_hires(
        fast_elements: list,
        threshold: float = 0.3,
        max_pages: int = None
    ) -> Set[int]:
        """
        Select pages that should use hi_res processing.
        
        Args:
            fast_elements: Elements from fast strategy scan
            threshold: Minimum score to qualify for hi_res (0-1)
            max_pages: Maximum number of pages to process with hi_res
            
        Returns:
            Set of page numbers to process with hi_res
        """
        page_scores = {}
        
        for element in fast_elements:
            # Get page number
            page_num = 0
            if hasattr(element, "metadata") and hasattr(element.metadata, "page_number"):
                page_num = element.metadata.page_number or 0
            
            # Analyze text content
            if hasattr(element, "text") and element.text:
                score = SmartPageSelector.analyze_text_for_visuals(element.text)
                
                # Accumulate score for this page
                if page_num not in page_scores:
                    page_scores[page_num] = 0.0
                page_scores[page_num] = max(page_scores[page_num], score)
        
        # Select pages above threshold
        selected_pages = {
            page for page, score in page_scores.items()
            if score >= threshold
        }
        
        # Limit to max_pages if specified
        if max_pages and len(selected_pages) > max_pages:
            # Sort by score and take top N
            sorted_pages = sorted(
                page_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            selected_pages = {page for page, _ in sorted_pages[:max_pages]}
        
        return selected_pages
    
    @staticmethod
    def should_use_hires_fallback(fast_elements: list) -> bool:
        """
        Determine if we should fallback to full hi_res processing.
        
        Returns True if:
        - Fast scan returned very few elements (possible extraction failure)
        - Document is very short (< 5 pages)
        """
        if not fast_elements:
            return True
        
        # Count unique pages
        pages = set()
        for element in fast_elements:
            if hasattr(element, "metadata") and hasattr(element.metadata, "page_number"):
                pages.add(element.metadata.page_number or 0)
        
        # If document is short, just use hi_res for everything
        if len(pages) <= 5:
            return True
        
        # If very few elements extracted, might be a problem
        if len(fast_elements) < 10:
            return True
        
        return False
