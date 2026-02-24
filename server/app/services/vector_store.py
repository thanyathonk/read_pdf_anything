import os
import shutil
import gc
import time
from typing import List, Optional, Dict
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from app.config import settings


class VectorStore:
    def __init__(self):
        self.stores: dict = {}  # pdf_id -> Chroma instance
        self._embedding_function = None  # Cache embedding function
    
    def _get_embedding_function(self):
        """Get Ollama embedding function"""
        if self._embedding_function is None:
            try:
                self._embedding_function = OllamaEmbeddings(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_EMBEDDING_MODEL
                )
                print(f"[Vector Store] Using Ollama embeddings: {settings.OLLAMA_EMBEDDING_MODEL}")
            except Exception as e:
                raise Exception(f"Failed to initialize Ollama embeddings: {e}. Make sure Ollama is running at {settings.OLLAMA_BASE_URL}")
        return self._embedding_function

    def _get_persist_directory(self, pdf_id: str, user_id: Optional[str] = None) -> str:
        """Get persist directory for PDF"""
        if user_id:
            return os.path.join(settings.PERSIST_DIRECTORY, f"user_{user_id}", pdf_id)
        else:
            return os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)

    def add_documents(
        self,
        pdf_id: str,
        documents: List[Document],
        persist_dir: str = None,
        user_id: Optional[str] = None,
    ):
        """Add documents to vector store"""
        try:
            persist_dir = persist_dir or self._get_persist_directory(pdf_id, user_id)

            # Use same store_key format as get_retriever
            store_key = f"{pdf_id}_{user_id}" if user_id else f"{pdf_id}_guest"

            # Remove old store if exists (check both old format and new format)
            if pdf_id in self.stores:
                self._close_store_by_key(pdf_id)
            if store_key in self.stores:
                self._close_store_by_key(store_key)

            if os.path.exists(persist_dir):
                self._safe_remove_dir(persist_dir)

            # Create new store with configured embedding function
            embedding_fn = self._get_embedding_function()
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=embedding_fn,
                persist_directory=persist_dir,
            )

            self.stores[store_key] = vector_store
            print(f"Vector store created for {pdf_id} (user_id: {user_id or 'guest'})")

        except Exception as e:
            raise Exception(f"Failed to add documents to vector store: {str(e)}")

    def get_retriever(self, pdf_id: str, k: int = None, user_id: Optional[str] = None):
        """Get retriever for PDF"""
        store_key = f"{pdf_id}_{user_id}" if user_id else f"{pdf_id}_guest"

        if store_key not in self.stores:
            # Try to load from disk - check both user and guest directories
            persist_dirs = []
            if user_id:
                persist_dirs.append(self._get_persist_directory(pdf_id, user_id))
            persist_dirs.append(
                self._get_persist_directory(pdf_id, None)
            )  # guest directory

            persist_dir = None
            for pd in persist_dirs:
                if os.path.exists(pd):
                    persist_dir = pd
                    break

            if persist_dir:
                embedding_fn = self._get_embedding_function()
                self.stores[store_key] = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=embedding_fn,
                )
            else:
                raise ValueError(f"Vector store not found for PDF: {pdf_id}")

        k = k or settings.TOP_K_CHUNKS
        return self.stores[store_key].as_retriever(search_kwargs={"k": k})
    
    def get_vectorstore(self, pdf_id: str, user_id: Optional[str] = None):
        """Get Chroma vectorstore instance directly (for similarity_search)"""
        store_key = f"{pdf_id}_{user_id}" if user_id else f"{pdf_id}_guest"
        
        if store_key not in self.stores:
            # Try to load from disk
            persist_dirs = []
            if user_id:
                persist_dirs.append(self._get_persist_directory(pdf_id, user_id))
            persist_dirs.append(self._get_persist_directory(pdf_id, None))
            
            persist_dir = None
            for pd in persist_dirs:
                if os.path.exists(pd):
                    persist_dir = pd
                    break
            
            if persist_dir:
                embedding_fn = self._get_embedding_function()
                self.stores[store_key] = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=embedding_fn,
                )
            else:
                raise ValueError(f"Vector store not found for PDF: {pdf_id}")
        
        return self.stores[store_key]
    
    def similarity_search(
        self, 
        pdf_id: str, 
        query: str, 
        k: int = None, 
        user_id: Optional[str] = None
    ) -> List[Document]:
        """Perform similarity search directly"""
        vectorstore = self.get_vectorstore(pdf_id, user_id)
        k = k or settings.TOP_K_CHUNKS
        return vectorstore.similarity_search(query, k=k)

    def _close_store(self, pdf_id: str):
        """Close and cleanup a specific store (legacy method - uses pdf_id as key)"""
        if pdf_id in self.stores:
            self._close_store_by_key(pdf_id)

    def _close_store_by_key(self, store_key: str):
        """Close and cleanup a specific store by key"""
        if store_key in self.stores:
            try:
                store = self.stores[store_key]
                # Try to delete the collection
                if hasattr(store, "_client") and store._client:
                    try:
                        store._client.delete_collection(store._collection.name)
                    except:
                        pass
                # Clear reference
                del self.stores[store_key]
                # Force garbage collection to release file handles
                gc.collect()
                # Small delay to allow OS to release file handles
                time.sleep(0.1)
            except Exception as e:
                print(f"Warning: Error closing store {store_key}: {e}")

    def _safe_remove_dir(self, dir_path: str, max_retries: int = 3):
        """Safely remove directory with retries"""
        for attempt in range(max_retries):
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                return True
            except PermissionError as e:
                if attempt < max_retries - 1:
                    gc.collect()
                    time.sleep(0.5 * (attempt + 1))  # Increasing delay
                else:
                    print(
                        f"Warning: Could not remove directory after {max_retries} attempts: {e}"
                    )
                    return False
        return False

    def remove_documents(self, pdf_id: str, user_id: Optional[str] = None):
        """Remove documents from vector store"""
        # Use same store_key format as get_retriever
        store_key = f"{pdf_id}_{user_id}" if user_id else f"{pdf_id}_guest"

        # Close the store first to release file handles
        if store_key in self.stores:
            self._close_store_by_key(store_key)

        # Remove from both user and guest directories (to be safe)
        if user_id:
            user_persist_dir = self._get_persist_directory(pdf_id, user_id)
            if os.path.exists(user_persist_dir):
                self._safe_remove_dir(user_persist_dir)
        guest_persist_dir = self._get_persist_directory(pdf_id, None)
        if os.path.exists(guest_persist_dir):
            self._safe_remove_dir(guest_persist_dir)


# Singleton instance
vector_store = VectorStore()
