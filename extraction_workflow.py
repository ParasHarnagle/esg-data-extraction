"""LangGraph-based extraction workflow for ESG indicators."""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
import operator
import logging
from pathlib import Path

from models import ESGIndicator, ExtractedValue, ESG_INDICATORS
from pdf_parser import PDFParser
from llm_client import OpenRouterClient, ESGExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExtractionState(TypedDict):
    """State for the extraction workflow."""
    # Input
    pdf_path: str
    company_name: str
    report_year: int
    indicators_to_extract: List[ESGIndicator]
    
    # Processing state
    current_indicator_index: int
    pdf_text_chunks: List[tuple[int, str]]  # (page_num, text)
    relevant_contexts: Dict[str, List[str]]  # indicator_code -> contexts
    
    # Output
    extracted_values: Annotated[List[ExtractedValue], operator.add]
    errors: Annotated[List[str], operator.add]
    processing_status: str


class ESGExtractionWorkflow:
    """LangGraph-based workflow for extracting ESG indicators."""
    
    def __init__(self):
        """Initialize the extraction workflow."""
        self.llm_client = OpenRouterClient()
        self.extractor = ESGExtractor(self.llm_client)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(ExtractionState)
        
        # Add nodes
        workflow.add_node("load_pdf", self.load_pdf_node)
        workflow.add_node("prepare_contexts", self.prepare_contexts_node)
        workflow.add_node("extract_indicator", self.extract_indicator_node)
        workflow.add_node("validate_and_store", self.validate_and_store_node)
        workflow.add_node("finalize", self.finalize_node)
        
        # Define flow
        workflow.set_entry_point("load_pdf")
        workflow.add_edge("load_pdf", "prepare_contexts")
        workflow.add_edge("prepare_contexts", "extract_indicator")
        workflow.add_conditional_edges(
            "extract_indicator",
            self.should_continue_extraction,
            {
                "continue": "extract_indicator",
                "validate": "validate_and_store"
            }
        )
        workflow.add_edge("validate_and_store", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def load_pdf_node(self, state: ExtractionState) -> Dict:
        """Load and parse PDF document."""
        logger.info(f"Loading PDF: {state['pdf_path']}")
        
        try:
            parser = PDFParser(state['pdf_path'])
            
            # Extract text with page numbers
            pages_text = parser.extract_text_with_pages()
            
            logger.info(f"Loaded {len(pages_text)} pages from PDF")
            
            return {
                "pdf_text_chunks": pages_text,
                "processing_status": "pdf_loaded"
            }
        
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            return {
                "errors": [f"PDF loading error: {str(e)}"],
                "processing_status": "error"
            }
    
    def prepare_contexts_node(self, state: ExtractionState) -> Dict:
        """Prepare relevant contexts for each indicator."""
        logger.info("Preparing contexts for indicators")
        
        relevant_contexts = {}
        
        try:
            pdf_path = state['pdf_path']
            parser = PDFParser(pdf_path)
            
            for indicator in state['indicators_to_extract']:
                # Search for relevant pages using keywords
                contexts = []
                
                # Use keyword search to find relevant sections
                relevant_pages = parser.extract_section_by_keywords(
                    keywords=indicator.keywords,
                    context_pages=1
                )
                
                # If no specific pages found, use chunked approach
                if not relevant_pages:
                    logger.warning(f"No specific pages found for {indicator.code}, using chunks")
                    chunks = parser.chunk_text(chunk_size=3000, overlap=300)
                    contexts = [chunk.text for chunk in chunks[:5]]  # Take first 5 chunks
                else:
                    contexts = [text for _, text in relevant_pages[:3]]  # Take top 3 pages
                
                relevant_contexts[indicator.code.value] = contexts
                logger.info(f"Found {len(contexts)} contexts for {indicator.code}")
            
            parser.close()
            
            return {
                "relevant_contexts": relevant_contexts,
                "current_indicator_index": 0,
                "processing_status": "contexts_prepared"
            }
        
        except Exception as e:
            logger.error(f"Error preparing contexts: {e}")
            return {
                "errors": [f"Context preparation error: {str(e)}"],
                "processing_status": "error"
            }
    
    def extract_indicator_node(self, state: ExtractionState) -> Dict:
        """Extract a single indicator."""
        idx = state['current_indicator_index']
        indicators = state['indicators_to_extract']
        
        if idx >= len(indicators):
            return {"processing_status": "extraction_complete"}
        
        indicator = indicators[idx]
        logger.info(f"Extracting indicator {idx + 1}/{len(indicators)}: {indicator.code}")
        
        try:
            # Get relevant contexts for this indicator
            contexts = state['relevant_contexts'].get(indicator.code.value, [])
            
            if not contexts:
                logger.warning(f"No contexts found for {indicator.code}")
                return {
                    "extracted_values": [ExtractedValue(
                        indicator_code=indicator.code.value,
                        confidence=0.0,
                        explanation="No relevant context found in document"
                    )],
                    "current_indicator_index": idx + 1
                }
            
            # Extract using LLM with retry logic
            result = self.extractor.extract_with_retry(
                indicator_name=indicator.name,
                indicator_description=indicator.description,
                expected_unit=indicator.expected_unit,
                context_list=contexts,
                keywords=indicator.keywords,
                max_attempts=min(3, len(contexts))
            )
            
            # Create ExtractedValue
            extracted_value = ExtractedValue(
                indicator_code=indicator.code.value,
                value=result.get("value"),
                numeric_value=result.get("numeric_value"),
                unit=result.get("unit"),
                confidence=result.get("confidence", 0.0),
                explanation=result.get("explanation"),
                source_text=result.get("source_text")
            )
            
            logger.info(f"Extracted {indicator.code}: {extracted_value.value} (confidence: {extracted_value.confidence})")
            
            return {
                "extracted_values": [extracted_value],
                "current_indicator_index": idx + 1
            }
        
        except Exception as e:
            logger.error(f"Error extracting {indicator.code}: {e}")
            return {
                "errors": [f"Extraction error for {indicator.code}: {str(e)}"],
                "current_indicator_index": idx + 1
            }
    
    def should_continue_extraction(self, state: ExtractionState) -> str:
        """Determine whether to continue extracting or move to validation."""
        idx = state['current_indicator_index']
        total = len(state['indicators_to_extract'])
        
        if idx < total:
            return "continue"
        return "validate"
    
    def validate_and_store_node(self, state: ExtractionState) -> Dict:
        """Validate extracted values and prepare for storage."""
        logger.info("Validating extracted values")
        
        try:
            extracted_values = state['extracted_values']
            
            # Validation logic
            validated_count = sum(1 for v in extracted_values if v.confidence > 0.5)
            total_count = len(extracted_values)
            
            logger.info(f"Validated {validated_count}/{total_count} values with >0.5 confidence")
            
            return {
                "processing_status": "validated"
            }
        
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "errors": [f"Validation error: {str(e)}"],
                "processing_status": "error"
            }
    
    def finalize_node(self, state: ExtractionState) -> Dict:
        """Finalize extraction and prepare output."""
        logger.info("Finalizing extraction")
        
        return {
            "processing_status": "complete"
        }
    
    def run(
        self,
        pdf_path: str,
        company_name: str,
        report_year: int,
        indicators: Optional[List[ESGIndicator]] = None
    ) -> Dict[str, Any]:
        """Run the extraction workflow.
        
        Args:
            pdf_path: Path to PDF file
            company_name: Company name
            report_year: Report year
            indicators: List of indicators to extract (defaults to all)
        
        Returns:
            Dictionary with extraction results
        """
        # Use all indicators if none specified
        if indicators is None:
            indicators = ESG_INDICATORS
        
        # Initialize state
        initial_state = ExtractionState(
            pdf_path=pdf_path,
            company_name=company_name,
            report_year=report_year,
            indicators_to_extract=indicators,
            current_indicator_index=0,
            pdf_text_chunks=[],
            relevant_contexts={},
            extracted_values=[],
            errors=[],
            processing_status="initialized"
        )
        
        # Run the workflow
        logger.info(f"Starting extraction workflow for {company_name} - {report_year}")
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            logger.info("Workflow completed successfully")
            
            return {
                "status": "success",
                "company_name": company_name,
                "report_year": report_year,
                "extracted_values": final_state.get("extracted_values", []),
                "errors": final_state.get("errors", []),
                "total_indicators": len(indicators),
                "processing_status": final_state.get("processing_status", "unknown")
            }
        
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            return {
                "status": "error",
                "company_name": company_name,
                "report_year": report_year,
                "extracted_values": [],
                "errors": [str(e)],
                "total_indicators": len(indicators),
                "processing_status": "error"
            }


def run_extraction(
    pdf_path: str,
    company_name: str,
    report_year: int,
    indicators: Optional[List[ESGIndicator]] = None
) -> Dict[str, Any]:
    """Convenience function to run extraction workflow.
    
    Args:
        pdf_path: Path to PDF file
        company_name: Company name
        report_year: Report year
        indicators: List of indicators to extract
    
    Returns:
        Extraction results
    """
    workflow = ESGExtractionWorkflow()
    return workflow.run(pdf_path, company_name, report_year, indicators)
