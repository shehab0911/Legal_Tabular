"""
Field extraction service using AI/LLM with citations and confidence scoring.
"""

import json
import re
import logging
import os
import string
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from difflib import SequenceMatcher
import google.generativeai as genai

# Try importing Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts fields from documents with citations and confidence scoring."""

    def __init__(self, llm_client=None):
        """
        Initialize extractor.
        
        Args:
            llm_client: Optional LLM client for extraction (ChatGPT, Claude, etc.)
        """
        self.llm_client = llm_client
        
        # Initialize Groq if API key is present
        self.groq_client = None
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = Groq(api_key=groq_api_key)
                self.groq_model = "llama-3.3-70b-versatile" # Primary: High performance
                self.groq_fallback_model = "llama-3.1-8b-instant" # Fallback: Fast/Lower limits
                logger.info(f"Groq LLM initialized successfully ({self.groq_model} with fallback to {self.groq_fallback_model})")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
        
        # Initialize Gemini if API key is present
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # Use gemini-1.5-flash as it is free, faster, and more capable
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini LLM initialized successfully (gemini-1.5-flash)")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None

    def extract_fields(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_definitions: List[Dict[str, Any]],
        document_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract fields from document with citations and confidence.
        
        Args:
            document_text: Full document text
            document_chunks: List of chunks with metadata
            field_definitions: List of fields to extract
            document_id: Document identifier
            
        Returns:
            List of extraction results with citations and confidence
        """
        results = []
        
        for field_def in field_definitions:
            field_name = field_def.get('name') or field_def.get('display_name') or ''
            raw_field_type = field_def.get('field_type', 'TEXT')
            if hasattr(raw_field_type, 'value'):
                raw_field_type = raw_field_type.value
            field_type = str(raw_field_type).upper()
            description = field_def.get('description', '')
            display_name = field_def.get('display_name', '')
            normalization_rules = field_def.get('normalization_rules') or {}
            validation_rules = field_def.get('validation_rules') or {}
            
            extraction = self._extract_single_field(
                document_text=document_text,
                document_chunks=document_chunks,
                field_name=field_name,
                field_type=field_type,
                description=description,
                display_name=display_name,
                document_id=document_id,
                normalization_rules=normalization_rules,
                validation_rules=validation_rules,
            )
            
            results.append(extraction)
        
        return results

    def _extract_single_field(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_name: str,
        field_type: str,
        description: str,
        display_name: str,
        document_id: str,
        normalization_rules: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract a single field with citations and confidence."""
        
        extraction_result = {'value': None, 'raw_text': None, 'confidence': 0.0}
        method = 'heuristic'

        try:
            # 1. Try Groq if available (User preference: Best Model)
            if self.groq_client:
                extraction_result = self._extract_with_groq(
                    document_text, field_name, field_type, description
                )
                method = 'groq'
                
                # Fallback to Gemini if Groq failed (returned no value) and Gemini is available
                # This handles Rate Limit (429) errors or extraction failures from Groq
                if not extraction_result.get('value') and self.gemini_model:
                    logger.info(f"Groq extraction failed/empty for {field_name}, attempting Gemini fallback")
                    gemini_result = self._extract_with_gemini(
                        document_text, field_name, field_type, description
                    )
                    if gemini_result.get('value'):
                        extraction_result = gemini_result
                        method = 'gemini_fallback'

            # 2. Try Gemini if Groq not available (Primary)
            elif self.gemini_model:
                extraction_result = self._extract_with_gemini(
                    document_text, field_name, field_type, description
                )
                method = 'gemini'
            
            # 3. Try generic LLM if others not available
            elif self.llm_client:
                extraction_result = self._extract_with_llm(
                    document_text, field_name, field_type, description
                )
                method = 'llm'

            # 4. Fallback to heuristics if LLM failed or returned nothing
            # Check if value is None, empty, or confidence is very low, or if it's a known noise phrase
            raw_val = extraction_result.get('value')
            is_noise = False
            if raw_val:
                clean_check = raw_val.lower().strip().rstrip('.')
                if clean_check in ['n/a', 'none', 'not found', 'no information found', 'unknown', 'not specified', 'not stated']:
                    is_noise = True
            
            if not raw_val or is_noise or extraction_result.get('confidence', 0.0) < 0.1:
                if method != 'heuristic':
                    logger.info(f"LLM extraction ({method}) failed/noise for {field_name}, falling back to heuristics")
                
                heuristic_result = self._extract_with_heuristics(
                    document_text, document_chunks, field_name, field_type, display_name
                )
                
                # Only override if heuristic found something
                if heuristic_result.get('value'):
                    extraction_result = heuristic_result
                    method = 'heuristic_fallback'
            
            extracted_value = extraction_result.get('value')
            # Clean extracted value to remove noise
            extracted_value = self._clean_extracted_value(extracted_value, field_type)
            
            raw_text = extraction_result.get('raw_text')
            confidence = extraction_result.get('confidence', 0.0)
            
            # Find and rank citations
            citations = self._find_citations(
                raw_text or extracted_value,
                document_chunks,
                document_id,
                top_k=3
            )
            
            # Normalize value
            normalized_value = self._normalize_value(extracted_value, field_type)
            
            # Validate and adjust confidence
            validation_score = self._validate_extraction(
                extracted_value, normalized_value, field_type
            )
            final_confidence = min(1.0, confidence * validation_score)
            
            return {
                'field_name': field_name,
                'field_type': field_type,
                'extracted_value': extracted_value,
                'raw_text': raw_text,
                'normalized_value': normalized_value,
                'confidence_score': final_confidence,
                'citations': citations,
                'extraction_metadata': {
                    'method': method,
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                }
            }
        except Exception as e:
            logger.error(f"Error extracting field {field_name}: {str(e)}")
            return {
                'field_name': field_name,
                'field_type': field_type,
                'extracted_value': None,
                'raw_text': None,
                'normalized_value': None,
                'confidence_score': 0.0,
                'citations': [],
                'error': str(e),
            }

    def _extract_with_gemini(
        self,
        document_text: str,
        field_name: str,
        field_type: str,
        description: str,
    ) -> Dict[str, Any]:
        """Extract field using Google Gemini LLM."""
        # Gemini 1.5 Flash has a large context window, so we can use more text
        # Limit to 50k chars to be safe but informative
        prompt = f"""
You are a legal expert extracting information from a contract.
Extract the following field:

Field: {field_name}
Type: {field_type}
Description: {description}

Context (Document Excerpt):
{document_text[:50000]}...

Instructions:
1. Analyze the context to find the best value for the field.
2. If not found, return null/None.
3. FOR TEXT/DESCRIPTION FIELDS (Summary, Purpose, Rights, Obligations):
   - Provide a clear, complete sentence (or max 2 sentences) summarizing the information.
   - Ensure the sentence is grammatically complete and starts with a capital letter.
   - Do NOT return fragments like "and Acceptance Agreement" or starting with lowercase.
   - Example: "Governs physical factory lease at Gigafactory."
4. FOR DATA FIELDS (Date, Currency, Entity, Boolean):
   - Extract the EXACT value.
   - Be concise.
5. Estimate confidence (0.0 to 1.0). If the value is found clearly, set confidence to 0.9 or 1.0.
6. CRITICAL: Fix OCR errors in the extracted value.
   - Example: "GIGAF ACT ORY" -> "GIGAFACTORY"
   - Example: "A M E N D E D" -> "AMENDED"
   - Example: "R ESTATED" -> "RESTATED"
   - Remove artifacts like "[\"Text\"]" or "(“Text”)".

Output strictly in JSON format (no markdown fences):
{{
    "value": "extracted value",
    "raw_text": "supporting text context",
    "confidence": 0.9
}}
"""
        try:
            response = self.gemini_model.generate_content(prompt)
            # Clean up response text to ensure it's valid JSON
            text = response.text.strip()
            
            # Find JSON block using regex
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
            if json_match:
                text = json_match.group(1)
            elif text.startswith('```'):
                # Fallback for simple fence
                if text.startswith('```json'):
                    text = text[7:]
                else:
                    text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
            
            result = json.loads(text.strip())
            
            # Default confidence to 0.9 if value exists but confidence is missing/zero
            confidence = float(result.get('confidence', 0.0))
            if result.get('value') and confidence < 0.1:
                confidence = 0.9
                
            return {
                'value': result.get('value'),
                'raw_text': result.get('raw_text'),
                'confidence': min(1.0, confidence),
            }
        except Exception as e:
            logger.error(f"Gemini extraction error for {field_name}: {str(e)}")
            return {'value': None, 'raw_text': None, 'confidence': 0.0}

    def _extract_with_groq(
        self,
        document_text: str,
        field_name: str,
        field_type: str,
        description: str,
    ) -> Dict[str, Any]:
        """Extract field using Groq LLM."""
        prompt = f"""
You are a legal expert extracting information from a contract.
Extract the following field:

Field: {field_name}
Type: {field_type}
Description: {description}

Context (Document Excerpt):
{document_text[:30000]}...

Instructions:
1. Analyze the context to find the best value for the field.
2. If not found, return null/None.
3. FOR TEXT/DESCRIPTION FIELDS (Summary, Purpose, Rights, Obligations):
   - Provide a clear, complete sentence (or max 2 sentences) summarizing the information.
   - Ensure the sentence is grammatically complete and starts with a capital letter.
   - Do NOT return fragments like "and Acceptance Agreement".
   - Example: "Governs physical factory lease at Gigafactory."
4. FOR DATA FIELDS (Date, Currency, Entity, Boolean):
   - Extract the EXACT value.
   - Be concise.
5. Estimate confidence (0.0 to 1.0). If the value is found clearly, set confidence to 0.9 or 1.0.
6. CRITICAL: Clean up the extracted text:
   - Fix OCR errors (e.g., "GIGAF ACT ORY" -> "GIGAFACTORY", "R ESTATED" -> "RESTATED", "L EASE" -> "LEASE").
   - Fix split words (e.g., "A M E N D E D" -> "AMENDED").
   - Remove random brackets/parentheses (e.g., "[\"Text\"]" -> "Text", "(“Text”)" -> "Text").
   - Convert ALL CAPS text to Title Case or Sentence Case (e.g., "AMENDED AND RESTATED" -> "Amended and Restated").
   - Remove section numbers/bullets from the start (e.g., "2. Term" -> "Term").

Output strictly in JSON format (no markdown fences):
{{
    "value": "extracted value",
    "raw_text": "supporting text context",
    "confidence": 0.9
}}
"""
        try:
            # Helper to run groq request
            def run_groq(model_name):
                return self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful legal assistant that extracts structured data from documents. Output strictly JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=model_name,
                    temperature=0.1,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )

            try:
                chat_completion = run_groq(self.groq_model)
            except Exception as e:
                # Check for rate limit error (usually 429)
                if "429" in str(e) or "rate limit" in str(e).lower():
                    logger.warning(f"Groq primary model rate limited ({self.groq_model}), attempting fallback to {self.groq_fallback_model}")
                    chat_completion = run_groq(self.groq_fallback_model)
                else:
                    raise e
            
            text = chat_completion.choices[0].message.content
            
            # Robust JSON extraction
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Try to find JSON block using regex if direct parse fails
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
                if json_match:
                    text = json_match.group(1)
                    result = json.loads(text)
                else:
                    # Last resort: try to find start and end braces
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                        result = json.loads(text)
                    else:
                        raise

            # Default confidence to 0.9 if value exists but confidence is missing/zero
            confidence = float(result.get('confidence', 0.0))
            if result.get('value') and confidence < 0.1:
                confidence = 0.9

            return {
                'value': result.get('value'),
                'raw_text': result.get('raw_text'),
                'confidence': min(1.0, confidence),
            }
        except Exception as e:
            logger.error(f"Groq extraction error for {field_name}: {str(e)}")
            return {'value': None, 'raw_text': None, 'confidence': 0.0}


    def _extract_with_llm(
        self,
        document_text: str,
        field_name: str,
        field_type: str,
        description: str,
    ) -> Dict[str, Any]:
        """Extract field using LLM."""
        prompt = f"""
Extract the following field from the legal document:

Field Name: {field_name}
Field Type: {field_type}
Description: {description}

Document:
{document_text[:5000]}...

Please provide:
1. The extracted value
2. The raw text from the document supporting this extraction
3. Your confidence score (0.0-1.0)

Respond in JSON format:
{{
    "value": "...",
    "raw_text": "...",
    "confidence": 0.0
}}
"""
        try:
            response = self.llm_client.complete(prompt)
            result = json.loads(response)
            return {
                'value': result.get('value'),
                'raw_text': result.get('raw_text'),
                'confidence': min(1.0, result.get('confidence', 0.0)),
            }
        except Exception as e:
            logger.error(f"LLM extraction error: {str(e)}")
            return {'value': None, 'raw_text': None, 'confidence': 0.0}

    def _extract_with_heuristics(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_name: str,
        field_type: str,
        display_name: str,
    ) -> Dict[str, Any]:
        """Extract field using heuristic patterns."""
        
        aliases = [field_name, display_name]
        derived_aliases = []
        for alias in aliases:
            if not alias:
                continue
            derived_aliases.append(alias)
            if '_' in alias:
                derived_aliases.append(alias.replace('_', ' '))
        patterns = self._get_patterns_for_field(field_name, field_type, derived_aliases)
        
        for pattern, confidence_boost in patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                extracted_value = match.group(1) if match.groups() else match.group(0)
                extracted_value = self._clean_extracted_value(extracted_value, field_type)
                if not extracted_value:
                    continue
                if field_type == 'TEXT' and len(extracted_value) < 20:
                    sentence = self._sentence_at_position(document_text, match.start())
                    if sentence:
                        extracted_value = sentence.strip()
                
                # Get context around match
                start = max(0, match.start() - 300)
                end = min(len(document_text), match.end() + 300)
                context = document_text[start:end]
                
                confidence = min(1.0, 0.6 + confidence_boost)
                
                return {
                    'value': extracted_value.strip(),
                    'raw_text': context.strip(),
                    'confidence': confidence,
                }
        
        for alias in derived_aliases:
            if not alias:
                continue
            alias_pattern = re.escape(alias)
            window_match = re.search(
                rf"{alias_pattern}\s*(?:[:\-]|is|means)?\s*(.+)",
                document_text,
                re.IGNORECASE,
            )
            if window_match:
                extracted_value = window_match.group(1).split('\n')[0][:500]
                extracted_value = self._clean_extracted_value(extracted_value, field_type)
                if not extracted_value:
                    continue
                context = document_text[
                    max(0, window_match.start() - 300):min(len(document_text), window_match.end() + 300)
                ]
                return {
                    'value': extracted_value.strip(),
                    'raw_text': context.strip(),
                    'confidence': 0.4,
                }
        
        sentence_match = self._find_sentence_by_alias(document_text, derived_aliases)
        if sentence_match:
            extracted_value = self._clean_extracted_value(sentence_match, field_type)
            if extracted_value:
                return {
                    'value': extracted_value.strip(),
                    'raw_text': sentence_match.strip(),
                    'confidence': 0.35,
                }
        
        # No match found
        return {'value': None, 'raw_text': None, 'confidence': 0.0}

    @staticmethod
    def _get_patterns_for_field(
        field_name: str,
        field_type: str,
        aliases: List[str],
    ) -> List[Tuple[str, float]]:
        """Get regex patterns for common legal fields."""
        patterns = []
        
        field_name_lower = field_name.lower()
        
        # Common field patterns
        if 'date' in field_name_lower or field_type == 'DATE':
            patterns = [
                (r'(\d{1,2}/\d{1,2}/\d{4})', 0.3),
                (r'(\d{4}-\d{2}-\d{2})', 0.3),
                (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 0.4),
                (r'(?:dated|dated as of|as of)\s+([A-Za-z0-9,\s]+?\d{4})', 0.3),
            ]
        elif 'party' in field_name_lower or 'parties' in field_name_lower:
            patterns = [
                (r'(?:by and between)\s+([A-Z][A-Za-z\s&.,]+?)\s+(?:and|AND)\s+([A-Z][A-Za-z\s&.,]+)', 0.4),
                (r'(?:Between|BETWEEN|between)\s+([A-Z][A-Za-z\s&.,]+?)\s+(?:and|AND)', 0.3),
                (r'(?:Party|PARTY):\s*([A-Z][A-Za-z\s&.,]+?)(?:\n|;)', 0.4),
            ]
        elif 'effective' in field_name_lower or 'term' in field_name_lower:
            patterns = [
                (r'(?:effective|Effective|EFFECTIVE)(?:\s+date)?[:\s]+([A-Za-z0-9\s,./\-]+?)(?:[,;]|and|on)', 0.3),
                (r'(?:term|Term|TERM)[:\s]+([A-Za-z0-9\s,./\-]+?)(?:[,;]|and|\n)', 0.3),
                (r'(?:expire|expiration|expiry)[:\s]+([A-Za-z0-9\s,./\-]+?)(?:[,;]|\n)', 0.3),
            ]
        elif 'currency' in field_name_lower or 'amount' in field_name_lower or field_type == 'CURRENCY':
            patterns = [
                (r'\$[\d,]+\.?\d*', 0.4),
                (r'(USD|EUR|GBP)[\s]*[\d,]+\.?\d*', 0.3),
                (r'(?:purchase price|consideration|price)[:\s]+\$?([\d,]+\.?\d*)', 0.4),
            ]
        elif 'governing law' in field_name_lower or 'law' in field_name_lower:
            patterns = [
                (r'governed by the laws of\s+([A-Za-z\s]+?)(?:\.|;|\n)', 0.4),
            ]
        elif 'confidential' in field_name_lower:
            patterns = [
                (r'(?:confidentiality|confidential)\s+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'termination' in field_name_lower or 'terminate' in field_name_lower:
            patterns = [
                (r'(?:termination|terminate)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'indemn' in field_name_lower:
            patterns = [
                (r'(?:indemnification|indemnify|indemnity)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'liable' in field_name_lower or 'liability' in field_name_lower:
            patterns = [
                (r'(?:liability|Liability|LIABLE)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|and|as)', 0.3),
            ]
        elif 'jurisdiction' in field_name_lower or 'venue' in field_name_lower:
            patterns = [
                (r'(?:jurisdiction|venue)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'governed by the laws of\s+([A-Za-z\s]+)', 0.4),
                (r'courts of\s+([A-Za-z\s,]+)\s+shall have', 0.4),
                (r'submit to the.*jurisdiction of\s+([A-Za-z\s,]+)', 0.4),
            ]
        elif 'notice' in field_name_lower:
            patterns = [
                (r'(?:notice|Notice)s? shall be sent to[:\s]+([A-Za-z0-9\s,\-$().%@]+?)(?:[.;]|\n)', 0.3),
                (r'Address for notices:?\s*([A-Za-z0-9\s,\-$().%@\n]+)', 0.3),
            ]
        elif 'assignment' in field_name_lower:
            patterns = [
                (r'(?:assignment|assign)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'may not assign.*without.*consent', 0.3),
            ]
        elif 'force majeure' in field_name_lower:
            patterns = [
                (r'(?:force majeure)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'events beyond.*control.*including\s+([A-Za-z0-9\s,\-$().%]+)', 0.3),
            ]
        elif 'dispute' in field_name_lower or 'arbitration' in field_name_lower:
            patterns = [
                (r'(?:dispute resolution|arbitration|mediation)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'disputes shall be resolved by\s+([A-Za-z\s]+)', 0.4),
            ]
        elif 'warranty' in field_name_lower or 'warranties' in field_name_lower:
            patterns = [
                (r'(?:warranties|warranty)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'represents and warrants that\s+([A-Za-z0-9\s,\-$().%]+)', 0.3),
            ]
        elif 'exclusivity' in field_name_lower or 'exclusive' in field_name_lower:
            patterns = [
                (r'(?:exclusivity|exclusive)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'change of control' in field_name_lower:
            patterns = [
                (r'(?:change of control)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'amendment' in field_name_lower or 'modification' in field_name_lower:
            patterns = [
                (r'(?:amendment|modification)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'severability' in field_name_lower:
            patterns = [
                (r'(?:severability)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'waiver' in field_name_lower:
            patterns = [
                (r'(?:waiver)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'survival' in field_name_lower:
            patterns = [
                (r'(?:survival)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'entire agreement' in field_name_lower:
            patterns = [
                (r'(?:entire agreement)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'audit' in field_name_lower:
            patterns = [
                (r'(?:audit rights?|right to audit)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'(?:Audit Policy)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.4),
                (r'keep.*books and records.*for a period of\s+([A-Za-z0-9\s]+)', 0.3),
            ]
        elif 'insurance' in field_name_lower:
            patterns = [
                (r'(?:insurance)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'maintain.*insurance.*coverage.*of at least\s+([A-Za-z0-9\s,$]+)', 0.3),
            ]
        elif 'liability cap' in field_name_lower or 'cap' in field_name_lower:
            patterns = [
                (r'(?:aggregate liability|liability cap)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'liability.*shall not exceed\s+([A-Za-z0-9\s,$]+)', 0.4),
            ]
        elif 'data privacy' in field_name_lower or 'privacy' in field_name_lower:
            patterns = [
                (r'(?:data privacy|data protection)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'non-solicitation' in field_name_lower or 'solicit' in field_name_lower:
            patterns = [
                (r'(?:non-solicitation|solicitation)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'shall not.*solicit.*employees', 0.3),
            ]
        elif 'non-compete' in field_name_lower or 'compete' in field_name_lower:
            patterns = [
                (r'(?:non-compete|non-competition)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'subcontract' in field_name_lower:
            patterns = [
                (r'(?:subcontracting|subcontract)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'intellectual property' in field_name_lower or 'ip rights' in field_name_lower:
            patterns = [
                (r'(?:intellectual property|ip rights)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
                (r'owns all right, title and interest in.*intellectual property', 0.3),
            ]
        elif 'publicity' in field_name_lower:
            patterns = [
                (r'(?:publicity)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        elif 'counterparts' in field_name_lower:
            patterns = [
                (r'(?:counterparts)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n)', 0.3),
            ]
        
        # Generic pattern for any field
        for alias in aliases:
            if alias:
                patterns.append((r'(?:' + re.escape(alias) + r')[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|\n|and)', 0.2))
        
        return patterns

    @staticmethod
    def _clean_extracted_value(value: Optional[str], field_type: str) -> Optional[str]:
        if not value:
            return None
        
        # Basic cleanup
        cleaned = value.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        
        # Remove leading punctuation and conjunctions (fix for ", data protection..." or "and data...")
        cleaned = cleaned.lstrip('.,;:-')
        cleaned = re.sub(r'^(?:and|or|but|because|so)\s+', '', cleaned.strip(), flags=re.IGNORECASE)
        # Fix specific user-reported junk "and,In", "and ii from"
        cleaned = re.sub(r'^(?:and,?\s*In)\s+', 'In ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^(?:and\s+ii\s+from)\s+', 'From ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^\d+\.+\.+', '', cleaned) # Remove "4....i" dots
        cleaned = re.sub(r'^\.+\s*', '', cleaned) # Remove leading dots
        cleaned = re.sub(r'^\d{2,}\s+', '', cleaned) # Remove "03 " leading numbers
        cleaned = cleaned.lstrip('.,;:-').strip()
        
        # Remove common markdown formatting
        cleaned = cleaned.replace('**', '').replace('*', '').replace('`', '')

        # Remove common LLM prefixes
        cleaned = re.sub(r'^(?:Here is the |The )?(?:extracted )?(?:value|answer)(?: is)?[:\s-]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^Extracted[:\s-]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^Answer[:\s-]*', '', cleaned, flags=re.IGNORECASE)
        
        # Fix common OCR artifacts
        
        # Normalize smart quotes
        cleaned = cleaned.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
        
        # 1. Remove bracketed content wrappers (keep content)
        #    User complained about "upper and lower case backets"
        #    Strategy: Remove brackets/parentheses/braces but keep the content inside.
        #    We do this via regex to handle multiple occurrences and nested-like structures (non-nested regex).
        
        # Remove square brackets
        cleaned = re.sub(r'\[\s*(.*?)\s*\]', r'\1', cleaned)
        # Remove parentheses
        cleaned = re.sub(r'\(\s*(.*?)\s*\)', r'\1', cleaned)
        # Remove curly braces
        cleaned = re.sub(r'\{\s*(.*?)\s*\}', r'\1', cleaned)
        
        # Remove enclosing quotes if they wrap the whole content
        cleaned = cleaned.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or \
           (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        # 2. Fix split words (e.g. "GIGAF ACT ORY" -> "GIGAFACTORY")
        repairs = {
            'GIGAF ACT ORY': 'GIGAFACTORY',
            'GIGA FACTORY': 'GIGAFACTORY',
            'R ESTATED': 'RESTATED',
            'REST ATED': 'RESTATED',
            'F ACT ORY': 'FACTORY',
            'F ACTORY': 'FACTORY',
            'FACT ORY': 'FACTORY',
            'L EASE': 'LEASE',
            'A GREEMENT': 'AGREEMENT',
            'C ONTRACT': 'CONTRACT',
            'P ARTY': 'PARTY',
            'E XECUTION': 'EXECUTION',
            'E FFECTIVE': 'EFFECTIVE',
            'S ERVICES': 'SERVICES',
            'L ICENSE': 'LICENSE',
            'A M E N D E D': 'AMENDED',
            'T E R M S': 'TERMS',
            'C O N D I T I O N S': 'CONDITIONS',
            'AMENDED AND RESTATED': 'Amended and Restated',
            'BETWE EN': 'BETWEEN',
            'WHET HER': 'WHETHER',
            'STATUT ORY': 'STATUTORY',
            'HEREB Y': 'HEREBY',
            'REPRESENT ATIONS': 'REPRESENTATIONS',
            'IN WITNESS WHEREOF': 'In Witness Whereof',
        }
        for bad, good in repairs.items():
            # Case insensitive replace
            cleaned = re.sub(re.escape(bad), good, cleaned, flags=re.IGNORECASE)
            
        # Generic split word fixer: look for "L E T T E R" pattern
        # Matches single letters separated by spaces
        cleaned = re.sub(r'\b([A-Z])\s+([A-Z])\s+([A-Z])\b', r'\1\2\3', cleaned) # 3 letters
        cleaned = re.sub(r'\b([A-Z])\s+([A-Z])\b', r'\1\2', cleaned) # 2 letters, be careful
            
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common trailing punctuation
        cleaned = cleaned.rstrip('.,;:')
        
        # Fix unclosed parentheses at the end (e.g. "This Lease (including...")
        if cleaned.count('(') > cleaned.count(')'):
            # If it ends with open parens/text, just close it or strip it?
            # If the open paren is near the end, maybe strip.
            last_open = cleaned.rfind('(')
            if len(cleaned) - last_open < 50:
                 # Check if we should close it
                 cleaned += ')'
        
        # Remove common noise strings
        noise_phrases = [
            'execution version', 'confidential', 'page', 'of', 
            'unknown', 'not found', 'none', 'n/a', 'undefined',
            'no information found', 'not specified', 'not stated'
        ]
        if cleaned.lower() in noise_phrases:
            return None
            
        if field_type == 'TEXT':
            # Remove common noise words if they are the ONLY content
            if cleaned.lower() in {'and', 'or', 'the', 'a', 'an', 'of', 'to', 'by'}:
                return None
                
            # Remove leading bullets or numbering
            cleaned = re.sub(r'^[\divx]+\.\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^(?:SECTION|ARTICLE)\s+[\d.]+\s*', '', cleaned, flags=re.IGNORECASE) # Remove SECTION 4...
            cleaned = re.sub(r'^[-•*]\s*', '', cleaned)
            
            # Remove leading "Title:" or "Name:" etc if captured
            cleaned = re.sub(r'^(?:title|name|date|amount|price)[:\s]+', '', cleaned, flags=re.IGNORECASE)

            # Deduplication: Check if the beginning of the text is repeated
            # e.g. "AMENDED... These Amended..."
            # Heuristic: split by space, if first 3 words are repeated within the first 20 words, it's likely a header+body dup.
            words = cleaned.split()
            if len(words) > 10:
                # Try to find the start of a sentence "These..." "This..."
                match = re.search(r'\b(These|This|The)\b', cleaned[5:], re.IGNORECASE)
                if match:
                    # If the text before "These" looks like a header (all caps or similar to what follows), cut it.
                    start_idx = match.start() + 5 # +5 because we searched from cleaned[5:]
                    preamble = cleaned[:start_idx].strip()
                    # If preamble is short or uppercase, remove it
                    if preamble.isupper() or len(preamble) < 100:
                        # Check similarity? No, just cut if it looks like a header
                        cleaned = cleaned[start_idx:]
            
            # CASE CONVERSION: "make it fresh complete sentence"
            # If the text is predominantly uppercase (allow some non-letters), convert to Sentence case or Title Case
            # Heuristic: if > 70% of letters are uppercase, it's probably an all-caps header.
            letters = [c for c in cleaned if c.isalpha()]
            if letters:
                upper_count = sum(1 for c in letters if c.isupper())
                if upper_count / len(letters) > 0.6: # Lowered threshold
                    # Convert to Title Case (Capitalize First Letter of Each Word) or Sentence case
                    
                    # Use regex to capitalize words, preserving punctuation
                    # This handles "“AMENDED" -> "“Amended" correctly unlike string.capwords/title
                    cleaned = re.sub(
                        r"[A-Za-z]+", 
                        lambda m: m.group(0).capitalize(), 
                        cleaned.lower()
                    )
                    
                    # Fix specific acronyms back to uppercase
                    acronyms = ['Llc', 'Inc', 'Lp', 'Ltd', 'Usa', 'Us', 'Uk', 'Eu', 'Gtc', 'Ceo', 'Cfo', 'Cto', 'Ii', 'Iii', 'Iv']
                    for acr in acronyms:
                        # Use word boundary to match exact words
                        cleaned = re.sub(r'\b' + re.escape(acr) + r'\b', acr.upper(), cleaned, flags=re.IGNORECASE)
            
            # TITLE CASE FIX: If the text is heavily Title Cased (e.g. "This Amended GTC Are Exclusive"), convert to Sentence case
            # Check if > 60% of words start with uppercase
            words = cleaned.split()
            if len(words) > 8:
                title_case_count = sum(1 for w in words if w and w[0].isupper())
                if title_case_count / len(words) > 0.6:
                    # It's likely a Title Case sentence. Convert to Sentence case (only first word cap).
                    # Exception: Acronyms
                    lower_words = []
                    for i, w in enumerate(words):
                        if i == 0:
                            lower_words.append(w) # Keep first word as is (likely capitalized)
                        elif w.upper() in ['GTC', 'LLC', 'INC', 'LP', 'USA', 'US', 'UK', 'EU', 'CEO', 'CFO', 'CTO', 'II', 'III', 'IV', 'Tesla', 'Seller']:
                            lower_words.append(w) # Keep known acronyms/proper nouns
                        else:
                            lower_words.append(w.lower())
                    cleaned = " ".join(lower_words)

            # Final Check: Ensure it starts with Capital
            if cleaned and cleaned[0].islower():
                cleaned = cleaned[0].upper() + cleaned[1:]

            if len(cleaned) < 3:  # Too short, check if it's not meaningful
                 # Allow short values if they look like initials or specific codes, but generally filter noise
                 if not re.match(r'^[A-Z0-9]+$', cleaned):
                     return None

        return cleaned

    @staticmethod
    def _find_sentence_by_alias(text: str, aliases: List[str]) -> Optional[str]:
        for alias in aliases:
            if not alias:
                continue
            pattern = re.compile(
                rf"([^.]*\b{re.escape(alias)}\b[^.]*\.)",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _sentence_at_position(text: str, position: int) -> Optional[str]:
        if position < 0 or position >= len(text):
            return None
        start = text.rfind('.', 0, position)
        end = text.find('.', position)
        if end == -1:
            end = min(len(text), position + 300)
        start = 0 if start == -1 else start + 1
        sentence = text[start:end].strip()
        if not sentence:
            return None
        return sentence[:400]

    def _find_citations(
        self,
        query_text: str,
        document_chunks: List[Dict[str, Any]],
        document_id: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find relevant citations in document chunks."""
        citations = []
        
        if not query_text:
            return citations
        
        # Score chunks by similarity to query
        scored_chunks = []
        query_tokens = set(query_text.lower().split())
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk.get('text', '')
            chunk_tokens = set(chunk_text.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(query_tokens & chunk_tokens)
            union = len(query_tokens | chunk_tokens)
            similarity = intersection / union if union > 0 else 0.0
            
            # Boost score if query text is directly in chunk
            if query_text.lower() in chunk_text.lower():
                similarity = min(1.0, similarity + 0.3)
            
            scored_chunks.append({
                'text': chunk_text,
                'similarity': similarity,
                'page': chunk.get('page_number', 1),
                'section': chunk.get('section', 'Main'),
                'chunk_id': str(i),
            })
        
        # Sort and get top-k
        scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        for i, chunk in enumerate(scored_chunks[:top_k]):
            if chunk['similarity'] > 0.0:
                citations.append({
                    'citation_text': chunk['text'][:500],
                    'page_number': chunk['page'],
                    'section_title': chunk['section'],
                    'relevance_score': chunk['similarity'],
                    'chunk_id': chunk['chunk_id'],
                })
        
        return citations

    @staticmethod
    def _normalize_value(value: Optional[str], field_type: str) -> Optional[str]:
        """Normalize extracted value based on field type."""
        if not value:
            return None
        
        value = value.strip()
        
        if field_type == 'DATE':
            # Try to normalize to YYYY-MM-DD format
            date_patterns = [
                (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(1):0>2}-{m.group(2):0>2}"),
                (r'(\d{4})-(\d{2})-(\d{2})', lambda m: m.group(0)),
                (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', 
                 lambda m: datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").strftime("%Y-%m-%d")),
            ]
            for pattern, normalizer in date_patterns:
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    try:
                        return normalizer(match)
                    except:
                        continue
        
        elif field_type == 'CURRENCY':
            # Extract numeric value
            match = re.search(r'\$?([\d,]+\.?\d*)', value)
            if match:
                num_str = match.group(1).replace(',', '')
                return f"USD {num_str}"
        
        elif field_type == 'BOOLEAN':
            value_lower = value.lower()
            if any(word in value_lower for word in ['yes', 'true', 'agreed', 'confirmed']):
                return 'true'
            elif any(word in value_lower for word in ['no', 'false', 'denied', 'rejected']):
                return 'false'
        
        elif field_type == 'ENTITY':
            # Capitalize properly
            return ' '.join(word.capitalize() for word in value.split())
        
        return value

    @staticmethod
    def _validate_extraction(
        extracted_value: Optional[str],
        normalized_value: Optional[str],
        field_type: str,
    ) -> float:
        """Validate extraction and return confidence adjustment."""
        if not extracted_value:
            return 0.0
        
        # Check if normalization was successful
        if not normalized_value:
            return 0.5
        
        # Type-specific validation
        if field_type == 'DATE':
            if re.match(r'\d{4}-\d{2}-\d{2}', normalized_value):
                return 1.0
            return 0.6
        
        elif field_type == 'CURRENCY':
            if 'USD' in normalized_value and re.search(r'[\d,]+\.?\d*', normalized_value):
                return 1.0
            return 0.6
        
        elif field_type == 'BOOLEAN':
            if normalized_value in ['true', 'false']:
                return 1.0
            return 0.5
        
        # Generic validation
        # If we have a value and it's not empty, it's likely good for TEXT/General fields
        # Don't penalize just because it's not a specific type
        return 1.0
