"""Vector-based semantic search for PDF documents."""
import numpy as np
from typing import List, Tuple, Optional
import hashlib
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """Semantic search using embeddings."""
    
    def __init__(self, cache_dir: str = "data/embeddings_cache"):
        """Initialize vector search with a small, fast embedding model."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a small, fast model (runs locally, no API needed)
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded")
        
        self.chunks = []
        self.embeddings = None
        self.metadata = []
    
    def _get_cache_path(self, pdf_path: str) -> Path:
        """Get cache file path for a PDF."""
        pdf_hash = hashlib.md5(pdf_path.encode()).hexdigest()
        return self.cache_dir / f"{pdf_hash}.pkl"
    
    def index_document(
        self,
        pdf_path: str,
        text_by_page: dict,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        force_reindex: bool = False
    ):
        """Index PDF document with caching.
        
        Args:
            pdf_path: Path to PDF file
            text_by_page: Dict mapping page_num to text
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            force_reindex: Skip cache and reindex
        """
        cache_path = self._get_cache_path(pdf_path)
        
        # Try to load from cache
        if not force_reindex and cache_path.exists():
            logger.info(f"Loading embeddings from cache: {cache_path}")
            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)
                self.chunks = cached['chunks']
                self.embeddings = cached['embeddings']
                self.metadata = cached['metadata']
            logger.info(f"Loaded {len(self.chunks)} chunks from cache")
            return
        
        # Create chunks from pages
        logger.info("Creating text chunks...")
        self.chunks = []
        self.metadata = []
        
        for page_num, text in sorted(text_by_page.items()):
            # Split page into overlapping chunks
            for i in range(0, len(text), chunk_size - chunk_overlap):
                chunk = text[i:i + chunk_size]
                if len(chunk.strip()) > 50:  # Skip very small chunks
                    self.chunks.append(chunk)
                    self.metadata.append({
                        'page': page_num,
                        'start': i,
                        'end': i + len(chunk)
                    })
        
        logger.info(f"Created {len(self.chunks)} chunks from {len(text_by_page)} pages")
        
        # Generate embeddings
        logger.info("Generating embeddings (this may take 30-60 seconds)...")
        self.embeddings = self.model.encode(
            self.chunks,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Save to cache
        logger.info(f"Saving embeddings to cache: {cache_path}")
        with open(cache_path, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'embeddings': self.embeddings,
                'metadata': self.metadata
            }, f)
        
        logger.info("Indexing complete")
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[str, int, float]]:
        """Semantic search for relevant chunks.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of (chunk_text, page_num, similarity_score)
        """
        if self.embeddings is None:
            raise ValueError("No document indexed. Call index_document() first.")
        
        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Compute cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            page = self.metadata[idx]['page']
            score = float(similarities[idx])
            results.append((chunk, page, score))
        
        return results
    
    def search_for_indicator(
        self,
        indicator_name: str,
        indicator_description: str,
        keywords: List[str],
        top_k: int = 3
    ) -> str:
        """Search for content relevant to an ESG indicator.
        
        Args:
            indicator_name: Name of the indicator
            indicator_description: Description
            keywords: List of keywords
            top_k: Number of chunks to return
        
        Returns:
            Combined text from top chunks with page numbers
        """
        # Create rich query combining name, description, and keywords
        query = f"{indicator_name}. {indicator_description}. Keywords: {', '.join(keywords)}"
        
        results = self.search(query, top_k=top_k)
        
        # Format results
        output = []
        seen_pages = set()
        
        for chunk, page, score in results:
            if page not in seen_pages:
                output.append(f"\n--- Page {page} (relevance: {score:.2f}) ---")
                seen_pages.add(page)
            output.append(chunk.strip())
        
        return "\n\n".join(output)
