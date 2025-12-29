"""LLM client for OpenRouter API integration."""
import json
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        """Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (defaults to settings)
            base_url: OpenRouter base URL (defaults to settings)
            default_model: Default model to use (defaults to settings)
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.default_model = default_model or settings.default_model
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> str:
        """Generate completion from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            model: Model to use (defaults to default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to force JSON output
        
        Returns:
            Generated text
        """
        model = model or self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info(f"Generating completion with model: {model}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else {"type": "text"}
            )
            
            # Check if response has error
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.get('message', 'Unknown error')
                error_code = response.error.get('code', 'Unknown')
                logger.error(f"API error: {error_code} - {error_msg}")
                raise ValueError(f"API error: {error_code} - {error_msg}")
            
            # Check if response has the expected structure
            if not response.choices:
                logger.error(f"No choices in response: {response}")
                raise ValueError("API returned empty choices")
            
            content = response.choices[0].message.content
            
            if content is None:
                logger.error(f"Content is None. Full response: {response}")
                logger.error(f"Message: {response.choices[0].message}")
                raise ValueError("API returned None content")
            
            logger.info(f"Generated {len(content)} characters")
            
            return content
        
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate JSON response from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Parsed JSON response
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response: {response}")
            raise
    
    def try_multiple_models(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        models: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> tuple[str, str]:
        """Try multiple models until one succeeds.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            models: List of models to try (defaults to backup models)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            json_mode: Whether to force JSON output
        
        Returns:
            Tuple of (response, model_used)
        """
        models = models or [self.default_model] + settings.backup_models
        
        last_error = None
        for i, model in enumerate(models):
            try:
                # Add small delay between attempts (except first)
                if i > 0:
                    time.sleep(2)
                
                logger.info(f"Trying model {i+1}/{len(models)}: {model}")
                response = self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )
                logger.info(f"✓ Successfully used model: {model}")
                return response, model
            except Exception as e:
                logger.warning(f"✗ Model {model} failed: {e}")
                last_error = e
                continue
        
        raise Exception(f"All {len(models)} models failed. Last error: {last_error}")


class ESGExtractor:
    """Specialized extractor for ESG indicators using LLM."""
    
    def __init__(self, client: Optional[OpenRouterClient] = None):
        """Initialize ESG extractor.
        
        Args:
            client: OpenRouter client (creates new one if None)
        """
        self.client = client or OpenRouterClient()
    
    def extract_indicator(
        self,
        indicator_name: str,
        indicator_description: str,
        expected_unit: str,
        context: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """Extract a specific ESG indicator from context.
        
        Args:
            indicator_name: Name of the indicator
            indicator_description: Description of what to extract
            expected_unit: Expected unit of measurement
            context: Text context to extract from
            keywords: Keywords related to the indicator
        
        Returns:
            Dictionary with extraction results
        """
        system_prompt = """You are an expert ESG data analyst specializing in extracting 
sustainability indicators from corporate reports. Your task is to carefully analyze 
the provided text and extract the requested indicator value with high accuracy."""
        
        user_prompt = f"""
Extract the following ESG indicator from the provided text context:

**Indicator**: {indicator_name}
**Description**: {indicator_description}
**Expected Unit**: {expected_unit}
**Related Keywords**: {', '.join(keywords)}

**Text Context**:
{context[:4000]}  

Please extract the indicator value and provide your response in the following JSON format:
{{
    "value": "the extracted value as a string (e.g., '1,234,567' or '12.5%')",
    "numeric_value": the value as a number (e.g., 1234567 or 12.5),
    "unit": "the unit of measurement (e.g., 'tCO2e', '%', 'employees')",
    "confidence": a confidence score between 0.0 and 1.0,
    "explanation": "brief explanation of where and how you found this value",
    "source_text": "the exact sentence or phrase containing the value",
    "found": true or false
}}

If the indicator is not found or cannot be extracted with confidence, set "found" to false 
and "confidence" to 0.0. Always provide the most accurate numeric value you can extract.
"""
        
        try:
            response = self.client.generate_json(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Validate response structure
            if not isinstance(response, dict):
                response = {"found": False, "confidence": 0.0}
            
            return response
        
        except Exception as e:
            logger.error(f"Error extracting indicator {indicator_name}: {e}")
            return {
                "found": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def extract_with_retry(
        self,
        indicator_name: str,
        indicator_description: str,
        expected_unit: str,
        context_list: List[str],
        keywords: List[str],
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """Extract indicator with retry logic across multiple context chunks.
        
        Args:
            indicator_name: Name of the indicator
            indicator_description: Description of what to extract
            expected_unit: Expected unit
            context_list: List of text contexts to try
            keywords: Keywords related to indicator
            max_attempts: Maximum number of contexts to try
        
        Returns:
            Best extraction result
        """
        best_result = {"found": False, "confidence": 0.0}
        
        for i, context in enumerate(context_list[:max_attempts]):
            logger.info(f"Extraction attempt {i+1} for {indicator_name}")
            
            result = self.extract_indicator(
                indicator_name=indicator_name,
                indicator_description=indicator_description,
                expected_unit=expected_unit,
                context=context,
                keywords=keywords
            )
            
            # Update best result if this one is better
            if result.get("confidence", 0.0) > best_result.get("confidence", 0.0):
                best_result = result
            
            # If we found it with high confidence, stop
            if result.get("found") and result.get("confidence", 0.0) > 0.8:
                break
        
        return best_result
