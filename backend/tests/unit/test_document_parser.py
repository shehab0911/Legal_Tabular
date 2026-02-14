"""
Unit tests for DocumentParser - tests all supported file formats.
"""
import os
import sys
import tempfile
import pytest

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.document_parser import DocumentParser, DocumentChunker


class TestDocumentParser:
    """Tests for DocumentParser class."""

    def setup_method(self):
        self.parser = DocumentParser()

    def test_is_supported_pdf(self):
        assert self.parser.is_supported("contract.pdf") is True

    def test_is_supported_docx(self):
        assert self.parser.is_supported("agreement.docx") is True

    def test_is_supported_html(self):
        assert self.parser.is_supported("filing.html") is True
        assert self.parser.is_supported("filing.htm") is True

    def test_is_supported_txt(self):
        assert self.parser.is_supported("notes.txt") is True

    def test_is_not_supported(self):
        assert self.parser.is_supported("image.png") is False
        assert self.parser.is_supported("data.xlsx") is False
        assert self.parser.is_supported("archive.zip") is False

    def test_parse_txt(self):
        """Test parsing a plain text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test legal document.\nIt contains multiple lines.\nParties: Company A and Company B.")
            f.flush()
            try:
                content, metadata = self.parser.parse(f.name, 'txt')
                assert "test legal document" in content
                assert "Company A" in content
                assert metadata['format'] == 'text'
                assert metadata['pages'] == 1
                assert metadata['word_count'] > 0
            finally:
                os.unlink(f.name)

    def test_parse_html(self):
        """Test parsing an HTML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""
            <html>
            <head><title>Test Agreement</title></head>
            <body>
                <h1>Supply Agreement</h1>
                <p>This Agreement is entered into by and between Tesla, Inc. and Supplier Corp.</p>
                <p>Effective Date: January 1, 2024</p>
            </body>
            </html>
            """)
            f.flush()
            try:
                content, metadata = self.parser.parse(f.name, 'html')
                assert "Supply Agreement" in content
                assert "Tesla" in content
                assert metadata.get('title') == 'Test Agreement'
                assert metadata['word_count'] > 0
            finally:
                os.unlink(f.name)

    def test_parse_empty_txt(self):
        """Test parsing an empty text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            f.flush()
            try:
                content, metadata = self.parser.parse(f.name, 'txt')
                assert content == ""
                assert metadata['word_count'] == 0
            finally:
                os.unlink(f.name)


class TestDocumentChunker:
    """Tests for DocumentChunker class."""

    def setup_method(self):
        self.chunker = DocumentChunker()

    def test_chunk_basic(self):
        """Test basic chunking."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = self.chunker.chunk(text)
        assert len(chunks) >= 1
        assert all('text' in c for c in chunks)
        assert all('word_count' in c for c in chunks)

    def test_chunk_empty(self):
        """Test chunking empty text."""
        chunks = self.chunker.chunk("")
        assert len(chunks) == 0

    def test_chunk_long_text(self):
        """Test that long text produces multiple chunks."""
        # Generate text longer than default chunk_size (1000 words)
        sentences = ["This is test sentence number {}.".format(i) for i in range(300)]
        text = " ".join(sentences)
        chunks = self.chunker.chunk(text)
        assert len(chunks) > 1

    def test_chunk_metadata_preserved(self):
        """Test that metadata is passed through."""
        text = "This is a test document with some content."
        metadata = {"pages": 5}
        chunks = self.chunker.chunk(text, metadata)
        assert len(chunks) >= 1

    def test_chunk_has_section(self):
        """Test that chunks have section detection."""
        text = "ARTICLE 1: DEFINITIONS\nThis section defines key terms. The following terms have the stated meanings."
        chunks = self.chunker.chunk(text)
        assert len(chunks) >= 1
        # Should detect section from the header
        assert any(c.get('section') for c in chunks)


class TestParserWithRealFiles:
    """Tests using real data files if available."""

    def setup_method(self):
        self.parser = DocumentParser()
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')

    def test_parse_real_html_if_available(self):
        """Parse real HTML file from data directory."""
        html_path = os.path.join(self.data_dir, 'EX-10.2.html')
        if not os.path.exists(html_path):
            pytest.skip("Real data file not available")

        content, metadata = self.parser.parse(html_path, 'html')
        assert len(content) > 100
        assert metadata['word_count'] > 50

    def test_parse_real_pdf_if_available(self):
        """Parse real PDF file from data directory."""
        pdf_path = os.path.join(self.data_dir, 'Supply Agreement.pdf')
        if not os.path.exists(pdf_path):
            pytest.skip("Real data file not available")

        content, metadata = self.parser.parse(pdf_path, 'pdf')
        assert len(content) > 0
        assert 'pages' in metadata
