"""
Image Store Service - Using InMemoryStore pattern for base64 images
Based on LangChain's multi-vector retriever pattern
"""
from typing import Dict, List, Optional
from langchain_core.stores import InMemoryStore
from langchain_core.documents import Document


class ImageStoreService:
    """
    Manages in-memory storage of base64 images
    Uses LangChain InMemoryStore for consistency with multi-vector pattern
    """
    
    def __init__(self):
        # One store per PDF
        self.stores: Dict[str, InMemoryStore] = {}
    
    def get_store(self, pdf_id: str) -> InMemoryStore:
        """Get or create InMemoryStore for a PDF"""
        if pdf_id not in self.stores:
            self.stores[pdf_id] = InMemoryStore()
        return self.stores[pdf_id]
    
    def add_images(self, pdf_id: str, images: List[Dict]):
        """
        Add base64 images to store
        
        Args:
            pdf_id: PDF identifier
            images: List of dicts with keys: element_id, base64, page
        """
        store = self.get_store(pdf_id)
        
        # Create documents for each image
        base64_docs = [
            Document(
                page_content=img["base64"],
                metadata={
                    "pdf_id": pdf_id,
                    "element_id": img["element_id"],
                    "page": img["page"],
                    "type": "image_base64",
                }
            )
            for img in images
        ]
        
        # Store using element_id as key
        store.mset([(doc.metadata["element_id"], doc) for doc in base64_docs])
        
        print(f"[Image Store] Added {len(images)} images for PDF {pdf_id}")
    
    def get_images(self, pdf_id: str, element_ids: List[str]) -> List[Document]:
        """
        Retrieve images by element IDs
        
        Args:
            pdf_id: PDF identifier
            element_ids: List of element IDs to retrieve
            
        Returns:
            List of Document objects containing base64 images
        """
        if pdf_id not in self.stores:
            return []
        
        store = self.get_store(pdf_id)
        return store.mget(element_ids)
    
    def get_image(self, pdf_id: str, element_id: str) -> Optional[Document]:
        """
        Retrieve a single image by element ID
        
        Args:
            pdf_id: PDF identifier
            element_id: Element ID to retrieve
            
        Returns:
            Document object containing base64 image, or None
        """
        images = self.get_images(pdf_id, [element_id])
        return images[0] if images and images[0] else None
    
    def delete_store(self, pdf_id: str):
        """Delete image store for a PDF"""
        if pdf_id in self.stores:
            del self.stores[pdf_id]
            print(f"[Image Store] Deleted store for PDF {pdf_id}")
    
    def get_all_images(self, pdf_id: str) -> Dict[str, str]:
        """
        Get all images for a PDF as a dict
        
        Returns:
            Dict of element_id -> base64
        """
        if pdf_id not in self.stores:
            return {}
        
        store = self.get_store(pdf_id)
        # InMemoryStore doesn't have a direct way to get all keys
        # So we'll use the internal store dict
        if hasattr(store, 'store'):
            result = {}
            for element_id, doc in store.store.items():
                if isinstance(doc, Document):
                    result[element_id] = doc.page_content
            return result
        return {}


# Singleton instance
image_store_service = ImageStoreService()
