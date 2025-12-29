"""Fast extraction mode using vector search + single LLM call per indicator."""
import logging
from typing import List, Dict, Any, Optional
from models import ESGIndicator, ExtractedValue
from vector_search import VectorSearchEngine
from llm_client import OpenRouterClient
from pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class FastVectorExtractor:
    """Fast ESG extraction using semantic search."""
    
    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        vector_engine: Optional[VectorSearchEngine] = None
    ):
        """Initialize fast extractor.
        
        Args:
            llm_client: LLM client for extraction
            vector_engine: Vector search engine
        """
        self.llm_client = llm_client or OpenRouterClient()
        self.vector_engine = vector_engine or VectorSearchEngine()
    
    def extract_indicator(
        self,
        indicator: ESGIndicator,
        pdf_path: str,
        top_k_chunks: int = 3
    ) -> ExtractedValue:
        """Extract single indicator using vector search.
        
        Args:
            indicator: ESG indicator to extract
            pdf_path: Path to PDF (used for cache key)
            top_k_chunks: Number of relevant chunks to retrieve
        
        Returns:
            ExtractedValue
        """
        logger.info(f"Fast extracting: {indicator.code}")
        
        # Get relevant context using semantic search
        context = self.vector_engine.search_for_indicator(
            indicator_name=indicator.name,
            indicator_description=indicator.description,
            keywords=indicator.keywords,
            top_k=top_k_chunks
        )
        
        # Single LLM call to extract from context
        prompt = f"""Extract the ESG indicator from the provided document context.

**Indicator:** {indicator.code} - {indicator.name}
**Description:** {indicator.description}
**Expected Unit:** {indicator.expected_unit}

**Document Context:**
{context}

**Instructions:**
1. Find the exact value for this indicator in the context
2. Extract the numeric value with its unit
3. Identify the page number where you found it
4. Provide confidence score (0.0 to 1.0)

Respond in this exact format:
VALUE: [extracted value with unit, or "Not found"]
PAGE: [page number, or "N/A"]
CONFIDENCE: [0.0 to 1.0]
REASONING: [brief explanation of what you found]"""

        try:
            response, model_used = self.llm_client.try_multiple_models(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse response
            result = self._parse_response(response, indicator)
            logger.info(f"Extracted {indicator.code}: {result.value} (confidence: {result.confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Fast extraction failed for {indicator.code}: {e}")
            return ExtractedValue(
                indicator_code=indicator.code,
                value=None,
                unit=indicator.expected_unit,
                confidence=0.0,
                source_page=None,
                extraction_method="vector_search_failed"
            )
    
    def _parse_response(self, response: str, indicator: ESGIndicator) -> ExtractedValue:
        """Parse LLM response into ExtractedValue."""
        value = None
        page = None
        confidence = 0.0
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('VALUE:'):
                value_str = line.split('VALUE:')[1].strip()
                if value_str.lower() not in ['not found', 'n/a', 'none']:
                    value = value_str
            elif line.startswith('PAGE:'):
                page_str = line.split('PAGE:')[1].strip()
                if page_str.lower() not in ['n/a', 'none']:
                    try:
                        page = int(page_str)
                    except:
                        pass
            elif line.startswith('CONFIDENCE:'):
                conf_str = line.split('CONFIDENCE:')[1].strip()
                try:
                    confidence = float(conf_str)
                except:
                    confidence = 0.5
        
        return ExtractedValue(
            indicator_code=indicator.code,
            value=value,
            unit=indicator.expected_unit,
            confidence=confidence,
            source_page=page,
            extraction_method="vector_search"
        )
    
    def extract_batch(
        self,
        indicators: List[ESGIndicator],
        pdf_path: str,
        pdf_parser: PDFParser
    ) -> List[ExtractedValue]:
        """Extract multiple indicators efficiently.
        
        Args:
            indicators: List of indicators to extract
            pdf_path: Path to PDF file
            pdf_parser: PDF parser with document loaded
        
        Returns:
            List of ExtractedValues
        """
        logger.info(f"Starting fast batch extraction for {len(indicators)} indicators")
        
        # Step 1: Index document (with caching)
        logger.info("Step 1/2: Indexing document...")
        text_by_page = {}
        total_pages = len(pdf_parser.doc)
        logger.info(f"Extracting text from {total_pages} pages...")
        for page_num in range(total_pages):
            # Extract text (PyMuPDF uses 0-based indexing)
            page = pdf_parser.doc[page_num]
            text = page.get_text()
            text_by_page[page_num + 1] = text  # Store with 1-based page numbers
        
        self.vector_engine.index_document(
            pdf_path=pdf_path,
            text_by_page=text_by_page,
            chunk_size=600,
            chunk_overlap=100
        )
        
        # Step 2: Extract each indicator (fast single-pass)
        logger.info("Step 2/2: Extracting indicators...")
        results = []
        for i, indicator in enumerate(indicators, 1):
            logger.info(f"Extracting {i}/{len(indicators)}: {indicator.code}")
            result = self.extract_indicator(indicator, pdf_path, top_k_chunks=3)
            results.append(result)
        
        logger.info(f"Batch extraction complete: {len(results)} indicators")
        return results
