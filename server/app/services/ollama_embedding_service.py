"""
Ollama Embedding Service - Local embedding generation using Ollama
"""
import requests
from typing import List
from app.config import settings


class OllamaEmbeddingService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama API"""
        try:
            url = f"{self.base_url}/api/embeddings"
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("embedding", [])
            
        except Exception as e:
            print(f"Error getting Ollama embedding: {e}")
            raise Exception(f"Ollama embedding failed: {str(e)}")
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a single query text"""
        return self._get_embedding(query)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            embeddings.append(embedding)
        return embeddings


# Singleton instance
ollama_embedding_service = OllamaEmbeddingService()
