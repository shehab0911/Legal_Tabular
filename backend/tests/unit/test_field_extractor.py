"""Unit tests for FieldExtractor – normalization, validation, heuristics, citations."""

import pytest
from src.services.field_extractor import FieldExtractor


class TestNormalization:
    """Tests for value normalization across field types."""

    def test_normalize_date_slash(self):
        assert FieldExtractor._normalize_value("01/15/2024", "DATE") == "2024-01-15"

    def test_normalize_date_iso(self):
        assert FieldExtractor._normalize_value("2024-01-15", "DATE") == "2024-01-15"

    def test_normalize_date_long_form(self):
        assert FieldExtractor._normalize_value("January 15, 2024", "DATE") == "2024-01-15"

    def test_normalize_currency(self):
        result = FieldExtractor._normalize_value("$5,000,000", "CURRENCY")
        assert "USD" in result
        assert "5000000" in result

    def test_normalize_boolean_yes(self):
        assert FieldExtractor._normalize_value("Yes, agreed", "BOOLEAN") == "true"

    def test_normalize_boolean_no(self):
        assert FieldExtractor._normalize_value("No", "BOOLEAN") == "false"

    def test_normalize_entity(self):
        result = FieldExtractor._normalize_value("acme corporation", "ENTITY")
        assert result == "Acme Corporation"

    def test_normalize_none_returns_none(self):
        assert FieldExtractor._normalize_value(None, "TEXT") is None

    def test_normalize_empty_returns_none(self):
        assert FieldExtractor._normalize_value("", "TEXT") is None


class TestValidation:
    """Tests for confidence validation adjustments."""

    def test_valid_date_high_confidence(self):
        score = FieldExtractor._validate_extraction("Jan 15, 2024", "2024-01-15", "DATE")
        assert score == 1.0

    def test_invalid_date_low_confidence(self):
        score = FieldExtractor._validate_extraction("sometime", "sometime", "DATE")
        assert score < 1.0

    def test_valid_currency_high(self):
        score = FieldExtractor._validate_extraction("$5M", "USD 5000000", "CURRENCY")
        assert score == 1.0

    def test_no_value_zero(self):
        score = FieldExtractor._validate_extraction(None, None, "TEXT")
        assert score == 0.0

    def test_no_normalized_penalized(self):
        score = FieldExtractor._validate_extraction("something", None, "DATE")
        assert score == 0.5

    def test_text_field_full_score(self):
        score = FieldExtractor._validate_extraction("Full text here", "Full text here", "TEXT")
        assert score == 1.0


class TestCleanExtractedValue:
    """Tests for value cleaning (OCR fixes, noise removal)."""

    def test_removes_noise_phrases(self):
        assert FieldExtractor._clean_extracted_value("N/A", "TEXT") is None
        assert FieldExtractor._clean_extracted_value("not found", "TEXT") is None
        assert FieldExtractor._clean_extracted_value("unknown", "TEXT") is None

    def test_fixes_ocr_split_words(self):
        result = FieldExtractor._clean_extracted_value("GIGAF ACT ORY", "TEXT")
        assert result is not None
        assert "GIGAFACTORY" in result.upper()

    def test_removes_brackets(self):
        result = FieldExtractor._clean_extracted_value('[Some Value]', "TEXT")
        assert result is not None
        assert "[" not in result

    def test_strips_markdown(self):
        result = FieldExtractor._clean_extracted_value("**Bold text**", "TEXT")
        assert result is not None
        assert "**" not in result

    def test_short_noise_removed(self):
        assert FieldExtractor._clean_extracted_value("and", "TEXT") is None
        assert FieldExtractor._clean_extracted_value("or", "TEXT") is None


class TestHeuristicExtraction:
    """Tests for regex-based heuristic extraction."""

    def test_extract_date_heuristic(self):
        extractor = FieldExtractor()
        text = "This agreement is effective as of January 15, 2024."
        result = extractor._extract_with_heuristics(text, [], "effective_date", "DATE", "Effective Date")
        assert result["value"] is not None
        # The heuristic may return a partial date, the full date, or a normalized form
        value_str = str(result["value"])
        assert any(kw in value_str for kw in ["2024", "January", "01-15", "01/15"]), f"Unexpected date value: {value_str}"
        assert result["confidence"] > 0.3

    def test_extract_currency_heuristic(self):
        extractor = FieldExtractor()
        text = "The total purchase price is $5,000,000."
        result = extractor._extract_with_heuristics(text, [], "amount", "CURRENCY", "Amount")
        assert result["value"] is not None
        assert "5,000,000" in result["value"] or "5000000" in result["value"]

    def test_extract_governing_law_heuristic(self):
        extractor = FieldExtractor()
        text = "This Agreement shall be governed by the laws of the State of Delaware."
        result = extractor._extract_with_heuristics(text, [], "governing_law", "TEXT", "Governing Law")
        assert result["value"] is not None
        assert "delaware" in result["value"].lower()

    def test_extract_no_match_returns_none(self):
        extractor = FieldExtractor()
        text = "Nothing relevant here at all."
        result = extractor._extract_with_heuristics(text, [], "insurance", "TEXT", "Insurance")
        assert result["value"] is None
        assert result["confidence"] == 0.0


class TestCitationFinding:
    """Tests for citation relevance scoring."""

    def test_finds_relevant_citation(self):
        extractor = FieldExtractor()
        chunks = [
            {"text": "The effective date is January 15, 2024", "page_number": 1, "section": "Header"},
            {"text": "Payment is due within 30 days", "page_number": 2, "section": "Payment"},
        ]
        citations = extractor._find_citations("January 15, 2024", chunks, "doc1", top_k=3)
        assert len(citations) > 0
        assert citations[0]["relevance_score"] > 0.0

    def test_citations_sorted_by_relevance(self):
        extractor = FieldExtractor()
        chunks = [
            {"text": "Unrelated content about weather", "page_number": 1, "section": "Misc"},
            {"text": "The amount payable is $100,000 dollars due on signing", "page_number": 2, "section": "Payment"},
            {"text": "Payment of $100,000 shall be made in installments", "page_number": 3, "section": "Payment"},
        ]
        citations = extractor._find_citations("$100,000 payment", chunks, "doc1", top_k=3)
        scores = [c["relevance_score"] for c in citations]
        assert scores == sorted(scores, reverse=True)

    def test_no_citations_for_empty_query(self):
        extractor = FieldExtractor()
        citations = extractor._find_citations("", [], "doc1")
        assert citations == []
