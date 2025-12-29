"""Agent-based extraction workflow with tools for autonomous ESG data extraction."""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain.tools import BaseTool, StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import operator
import logging
from pathlib import Path
import json

from models import ESGIndicator, ExtractedValue, ESG_INDICATORS
from pdf_parser import PDFParser, TableExtractor
from llm_client import OpenRouterClient
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# TOOL DEFINITIONS - What the agent can use
# ============================================================================

class SearchPDFTool(BaseTool):
    """Tool for searching PDF content by keywords."""
    name: str = "search_pdf"
    description: str = """Searches the PDF for pages containing specific keywords.
    Use this to find relevant sections of the document.
    Input: JSON with 'query' field containing search terms.
    Returns: List of page numbers and text snippets where keywords were found."""
    
    pdf_parser: Optional[PDFParser] = None
    
    def _run(self, query: str) -> str:
        """Search PDF for keywords."""
        if not self.pdf_parser:
            return json.dumps({"error": "PDF not loaded"})
        
        try:
            results = self.pdf_parser.search_text(query, case_sensitive=False)
            
            if not results:
                return json.dumps({
                    "found": False,
                    "message": f"No pages found containing '{query}'"
                })
            
            # Return page numbers and context
            search_results = []
            for page_num, context in results[:5]:  # Top 5 results
                search_results.append({
                    "page": page_num,
                    "context": context[:500]  # First 500 chars
                })
            
            return json.dumps({
                "found": True,
                "total_pages": len(results),
                "results": search_results
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _arun(self, query: str) -> str:
        return self._run(query)


class GetPageContentTool(BaseTool):
    """Tool for retrieving full content from specific page."""
    name: str = "get_page_content"
    description: str = """Retrieves the full text content from a specific page number.
    Use this after finding relevant pages to get detailed content.
    Input: JSON with 'page_number' field (integer).
    Returns: Full text content of that page."""
    
    pdf_parser: Optional[PDFParser] = None
    
    def _run(self, page_number: int) -> str:
        """Get content from specific page."""
        if not self.pdf_parser:
            return json.dumps({"error": "PDF not loaded"})
        
        try:
            # Convert to 0-indexed
            page_idx = int(page_number) - 1
            
            if page_idx < 0 or page_idx >= len(self.pdf_parser.doc):
                return json.dumps({
                    "error": f"Page {page_number} out of range (1-{len(self.pdf_parser.doc)})"
                })
            
            text = self.pdf_parser.extract_text_by_page(page_idx)
            
            return json.dumps({
                "page": page_number,
                "content": text[:4000]  # Limit to 4000 chars
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _arun(self, page_number: int) -> str:
        return self._run(page_number)


class ExtractTableTool(BaseTool):
    """Tool for extracting tables from a specific page."""
    name: str = "extract_table"
    description: str = """Extracts structured tables from a specific page.
    Use this when you find data in tabular format.
    Input: JSON with 'page_number' field (integer).
    Returns: Extracted tables in structured format."""
    
    pdf_path: Optional[str] = None
    
    def _run(self, page_number: int) -> str:
        """Extract tables from page."""
        if not self.pdf_path:
            return json.dumps({"error": "PDF path not set"})
        
        try:
            extractor = TableExtractor(self.pdf_path)
            page_idx = int(page_number) - 1
            
            tables = extractor.extract_all_tables()
            
            if page_number not in tables:
                return json.dumps({
                    "found": False,
                    "message": f"No tables found on page {page_number}"
                })
            
            page_tables = tables[page_number]
            
            # Convert to readable format
            formatted_tables = []
            for i, table in enumerate(page_tables):
                formatted_tables.append({
                    "table_number": i + 1,
                    "rows": len(table),
                    "columns": len(table[0]) if table else 0,
                    "data": table[:10]  # First 10 rows
                })
            
            return json.dumps({
                "found": True,
                "page": page_number,
                "num_tables": len(formatted_tables),
                "tables": formatted_tables
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _arun(self, page_number: int) -> str:
        return self._run(page_number)


class GetPageRangeTool(BaseTool):
    """Tool for getting content from multiple consecutive pages."""
    name: str = "get_page_range"
    description: str = """Retrieves content from a range of pages.
    Use this when relevant information spans multiple pages.
    Input: JSON with 'start_page' and 'end_page' fields (integers).
    Returns: Combined text from all pages in range."""
    
    pdf_parser: Optional[PDFParser] = None
    
    def _run(self, start_page: int, end_page: int) -> str:
        """Get content from page range."""
        if not self.pdf_parser:
            return json.dumps({"error": "PDF not loaded"})
        
        try:
            text = self.pdf_parser.get_page_range_text(
                int(start_page),
                int(end_page)
            )
            
            return json.dumps({
                "start_page": start_page,
                "end_page": end_page,
                "content": text[:6000]  # Limit to 6000 chars
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _arun(self, start_page: int, end_page: int) -> str:
        return self._run(start_page, end_page)


class SearchByKeywordsTool(BaseTool):
    """Tool for searching with multiple related keywords."""
    name: str = "search_by_keywords"
    description: str = """Searches PDF using multiple related keywords at once.
    Use this to find sections relevant to an indicator using all its keywords.
    Input: JSON with 'keywords' field (list of strings).
    Returns: Pages containing any of the keywords."""
    
    pdf_parser: Optional[PDFParser] = None
    
    def _run(self, keywords: List[str]) -> str:
        """Search with multiple keywords."""
        if not self.pdf_parser:
            return json.dumps({"error": "PDF not loaded"})
        
        try:
            results = self.pdf_parser.extract_section_by_keywords(
                keywords=keywords,
                context_pages=1
            )
            
            if not results:
                return json.dumps({
                    "found": False,
                    "message": f"No pages found containing keywords: {keywords}"
                })
            
            search_results = []
            for page_num, text in results[:5]:
                search_results.append({
                    "page": page_num,
                    "content": text[:800]
                })
            
            return json.dumps({
                "found": True,
                "keywords_used": keywords,
                "total_pages": len(results),
                "results": search_results
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _arun(self, keywords: List[str]) -> str:
        return self._run(keywords)


# ============================================================================
# AGENT STATE
# ============================================================================

class AgentExtractionState(TypedDict):
    """State for agent-based extraction."""
    # Input
    pdf_path: str
    company_name: str
    report_year: int
    indicators_to_extract: List[ESGIndicator]
    
    # Agent state
    current_indicator: Optional[ESGIndicator]
    current_indicator_index: int
    messages: Annotated[List, operator.add]  # Conversation history
    
    # Tools state
    pdf_parser: Optional[PDFParser]
    
    # Output
    extracted_values: Annotated[List[ExtractedValue], operator.add]
    errors: Annotated[List[str], operator.add]
    processing_status: str


# ============================================================================
# AGENT-BASED WORKFLOW
# ============================================================================

class AgentESGExtractionWorkflow:
    """Agent-based workflow where LLM decides how to extract data."""
    
    def __init__(self):
        """Initialize the agent workflow."""
        self.llm_client = OpenRouterClient()
        self.graph = self._build_graph()
    
    def _create_tools(self, pdf_parser: PDFParser, pdf_path: str) -> List[BaseTool]:
        """Create tools for the agent."""
        search_tool = SearchPDFTool()
        search_tool.pdf_parser = pdf_parser
        
        page_tool = GetPageContentTool()
        page_tool.pdf_parser = pdf_parser
        
        table_tool = ExtractTableTool()
        table_tool.pdf_path = pdf_path
        
        range_tool = GetPageRangeTool()
        range_tool.pdf_parser = pdf_parser
        
        keywords_tool = SearchByKeywordsTool()
        keywords_tool.pdf_parser = pdf_parser
        
        return [search_tool, page_tool, table_tool, range_tool, keywords_tool]
    
    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph."""
        workflow = StateGraph(AgentExtractionState)
        
        # Add nodes
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("agent_extract", self.agent_extract_node)
        workflow.add_node("finalize", self.finalize_node)
        
        # Define flow
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "agent_extract")
        workflow.add_conditional_edges(
            "agent_extract",
            self.should_continue,
            {
                "continue": "agent_extract",
                "finalize": "finalize"
            }
        )
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def initialize_node(self, state: AgentExtractionState) -> Dict:
        """Initialize PDF parser and tools."""
        logger.info(f"Initializing agent workflow for {state['pdf_path']}")
        
        try:
            parser = PDFParser(state['pdf_path'])
            
            return {
                "pdf_parser": parser,
                "current_indicator_index": 0,
                "processing_status": "initialized",
                "messages": []
            }
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return {
                "errors": [f"Initialization error: {str(e)}"],
                "processing_status": "error"
            }
    
    def agent_extract_node(self, state: AgentExtractionState) -> Dict:
        """Agent autonomously extracts an indicator using tools."""
        idx = state['current_indicator_index']
        indicators = state['indicators_to_extract']
        
        if idx >= len(indicators):
            return {"processing_status": "complete"}
        
        indicator = indicators[idx]
        logger.info(f"Agent extracting indicator {idx + 1}/{len(indicators)}: {indicator.code}")
        
        try:
            # Create tools for this extraction
            tools = self._create_tools(state['pdf_parser'], state['pdf_path'])
            
            # Create agent prompt
            system_message = f"""You are an expert ESG data extraction agent. Your task is to autonomously 
extract the following indicator from a sustainability report.

**Indicator**: {indicator.name} ({indicator.code})
**Description**: {indicator.description}
**Expected Unit**: {indicator.expected_unit}
**Keywords to search**: {', '.join(indicator.keywords)}

**Available Tools**:
- search_pdf: Search for keywords in the document
- get_page_content: Get full text from a specific page
- extract_table: Extract tables from a page
- get_page_range: Get content from multiple pages
- search_by_keywords: Search using multiple keywords at once

**Your Task**:
1. Decide which tool(s) to use to find this indicator
2. Search the document strategically
3. Extract the value when you find it
4. Return the result in JSON format

**Important**: 
- Think step by step about where this data might be located
- Use tools efficiently (don't request every page)
- After using 2-3 tools, you should have enough information to provide a final answer
- When you find the value, YOU MUST respond with FINAL ANSWER: followed by the JSON
- Use this EXACT JSON format for your final answer:
{{
    "value": "the extracted value as string",
    "numeric_value": the numeric value as float (or null),
    "unit": "the unit",
    "confidence": 0.0 to 1.0 (how confident you are),
    "explanation": "how and where you found it including page number",
    "source_page": page number where found,
    "found": true or false
}}

**Examples of good final answers**:
FINAL ANSWER: {{"value": "1,234 tCO2e", "numeric_value": 1234, "unit": "tCO2e", "confidence": 0.95, "explanation": "Found in emissions table on page 77", "source_page": 77, "found": true}}

FINAL ANSWER: {{"found": false, "confidence": 0.0, "explanation": "Searched pages 50-80 but could not find this indicator"}}

Begin your extraction process now."""

            user_message = f"Extract the indicator: {indicator.name}"
            
            # Call agent with tools
            result = self._run_agent_with_tools(
                system_message=system_message,
                user_message=user_message,
                tools=tools,
                indicator=indicator
            )
            
            # Parse result
            # Handle both string and enum for indicator.code
            indicator_code = indicator.code.value if hasattr(indicator.code, 'value') else indicator.code
            
            if result and result.get("found"):
                extracted_value = ExtractedValue(
                    indicator_code=indicator_code,
                    value=result.get("value"),
                    numeric_value=result.get("numeric_value"),
                    unit=result.get("unit"),
                    confidence=result.get("confidence", 0.5),
                    explanation=result.get("explanation"),
                    source_page=result.get("source_page")
                )
            else:
                extracted_value = ExtractedValue(
                    indicator_code=indicator_code,
                    confidence=0.0,
                    explanation="Agent could not find this indicator"
                )
            
            logger.info(f"Agent extracted {indicator_code}: confidence={extracted_value.confidence}")
            
            return {
                "extracted_values": [extracted_value],
                "current_indicator_index": idx + 1
            }
        
        except Exception as e:
            logger.error(f"Agent extraction error for {indicator.code}: {e}")
            return {
                "errors": [f"Agent error for {indicator.code}: {str(e)}"],
                "current_indicator_index": idx + 1
            }
    
    def _run_agent_with_tools(
        self,
        system_message: str,
        user_message: str,
        tools: List[BaseTool],
        indicator: ESGIndicator
    ) -> Dict:
        """Run the agent with tool calling capability."""
        
        # Create a simple ReAct-style agent loop
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        max_iterations = 8  # Increased from 5 to allow more tool exploration
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent iteration {iteration}/{max_iterations}")
            
            # Get agent response
            prompt = self._format_messages_with_tools(messages, tools)
            
            # Try multiple models as fallback
            try:
                response, model_used = self.llm_client.try_multiple_models(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=2000
                )
                logger.info(f"Used model: {model_used}")
            except Exception as e:
                logger.error(f"All models failed: {e}")
                raise
            
            # Check if agent wants to use a tool
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                # Execute tool
                tool_name = tool_call["tool"]
                tool_input = tool_call["input"]
                
                logger.info(f"Agent calling tool: {tool_name} with input: {tool_input}")
                
                tool_result = self._execute_tool(tool_name, tool_input, tools)
                
                # Add tool result to messages
                messages.append({
                    "role": "assistant",
                    "content": f"I'll use {tool_name} with input: {tool_input}"
                })
                messages.append({
                    "role": "tool",
                    "content": f"Tool result: {tool_result}"
                })
            else:
                # No tool call - agent is providing final answer
                final_result = self._parse_final_answer(response)
                if final_result:
                    return final_result
                
                # Ask agent to provide final answer
                messages.append({
                    "role": "user",
                    "content": "Please provide your final answer in the JSON format specified."
                })
        
        # Max iterations reached
        return {"found": False, "confidence": 0.0, "explanation": "Max iterations reached"}
    
    def _format_messages_with_tools(self, messages: List[Dict], tools: List[BaseTool]) -> str:
        """Format conversation with tool descriptions."""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in tools
        ])
        
        conversation = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        return f"""{conversation}

Available tools:
{tools_desc}

To use a tool, respond with:
TOOL: tool_name
INPUT: {{"param": "value"}}

To provide final answer, respond with:
FINAL ANSWER: {{"value": "...", "unit": "...", "confidence": 0.95, ...}}

Your response:"""
    
    def _parse_tool_call(self, response: str) -> Optional[Dict]:
        """Parse if agent wants to call a tool."""
        if "TOOL:" in response and "INPUT:" in response:
            try:
                lines = response.split("\n")
                tool_line = [l for l in lines if l.startswith("TOOL:")][0]
                input_line = [l for l in lines if l.startswith("INPUT:")][0]
                
                tool_name = tool_line.replace("TOOL:", "").strip()
                input_str = input_line.replace("INPUT:", "").strip()
                tool_input = json.loads(input_str)
                
                return {"tool": tool_name, "input": tool_input}
            except Exception as e:
                logger.warning(f"Failed to parse tool call: {e}")
        
        return None
    
    def _execute_tool(self, tool_name: str, tool_input: Dict, tools: List[BaseTool]) -> str:
        """Execute a tool."""
        tool = next((t for t in tools if t.name == tool_name), None)
        
        if not tool:
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        try:
            # Extract parameters based on tool
            if tool_name == "search_pdf":
                return tool._run(tool_input.get("query", ""))
            elif tool_name == "get_page_content":
                return tool._run(tool_input.get("page_number", 1))
            elif tool_name == "extract_table":
                return tool._run(tool_input.get("page_number", 1))
            elif tool_name == "get_page_range":
                return tool._run(
                    tool_input.get("start_page", 1),
                    tool_input.get("end_page", 1)
                )
            elif tool_name == "search_by_keywords":
                return tool._run(tool_input.get("keywords", []))
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _parse_final_answer(self, response: str) -> Optional[Dict]:
        """Parse final answer from agent."""
        if "FINAL ANSWER:" in response:
            try:
                json_start = response.index("{")
                json_end = response.rindex("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            except Exception as e:
                logger.warning(f"Failed to parse final answer: {e}")
        
        # Try to parse as direct JSON
        try:
            return json.loads(response)
        except:
            pass
        
        return None
    
    def should_continue(self, state: AgentExtractionState) -> str:
        """Determine if we should continue extracting."""
        idx = state['current_indicator_index']
        total = len(state['indicators_to_extract'])
        
        if idx < total:
            return "continue"
        return "finalize"
    
    def finalize_node(self, state: AgentExtractionState) -> Dict:
        """Finalize extraction."""
        logger.info("Agent workflow complete")
        
        # Close PDF parser
        if state.get('pdf_parser'):
            state['pdf_parser'].close()
        
        return {"processing_status": "complete"}
    
    def run(
        self,
        pdf_path: str,
        company_name: str,
        report_year: int,
        indicators: Optional[List[ESGIndicator]] = None
    ) -> Dict[str, Any]:
        """Run the agent-based extraction workflow."""
        if indicators is None:
            indicators = ESG_INDICATORS
        
        initial_state = AgentExtractionState(
            pdf_path=pdf_path,
            company_name=company_name,
            report_year=report_year,
            indicators_to_extract=indicators,
            current_indicator_index=0,
            current_indicator=None,
            messages=[],
            pdf_parser=None,
            extracted_values=[],
            errors=[],
            processing_status="initialized"
        )
        
        logger.info(f"Starting AGENT-BASED extraction for {company_name} - {report_year}")
        logger.info(f"Agent will autonomously decide how to extract {len(indicators)} indicators")
        
        try:
            final_state = self.graph.invoke(initial_state)
            
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
            logger.error(f"Agent workflow error: {e}")
            return {
                "status": "error",
                "company_name": company_name,
                "report_year": report_year,
                "extracted_values": [],
                "errors": [str(e)],
                "total_indicators": len(indicators),
                "processing_status": "error"
            }


def run_agent_extraction(
    pdf_path: str,
    company_name: str,
    report_year: int,
    indicators: Optional[List[ESGIndicator]] = None
) -> Dict[str, Any]:
    """Convenience function to run agent-based extraction."""
    workflow = AgentESGExtractionWorkflow()
    return workflow.run(pdf_path, company_name, report_year, indicators)
