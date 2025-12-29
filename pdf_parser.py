"""PDF parsing and text extraction utilities."""
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import re
from dataclasses import dataclass


@dataclass
class PDFChunk:
    """Represents a chunk of text from a PDF."""
    text: str
    page_number: int
    start_char: int
    end_char: int
    metadata: Dict[str, any]


@dataclass
class PDFMetadata:
    """PDF document metadata."""
    total_pages: int
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None


class PDFParser:
    """Main PDF parsing class using PyMuPDF and pdfplumber."""
    
    def __init__(self, pdf_path: str):
        """Initialize parser with PDF file path."""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = fitz.open(str(self.pdf_path))
        self.metadata = self._extract_metadata()
    
    def _extract_metadata(self) -> PDFMetadata:
        """Extract PDF metadata."""
        meta = self.doc.metadata
        return PDFMetadata(
            total_pages=len(self.doc),
            author=meta.get('author'),
            title=meta.get('title'),
            subject=meta.get('subject'),
            creator=meta.get('creator'),
            producer=meta.get('producer'),
            creation_date=meta.get('creationDate')
        )
    
    def extract_text_by_page(self, page_num: int) -> str:
        """Extract text from a specific page."""
        if page_num < 0 or page_num >= len(self.doc):
            raise ValueError(f"Page number {page_num} out of range")
        
        page = self.doc[page_num]
        return page.get_text()
    
    def extract_all_text(self) -> str:
        """Extract text from all pages."""
        all_text = []
        for page_num in range(len(self.doc)):
            text = self.extract_text_by_page(page_num)
            all_text.append(f"\n--- Page {page_num + 1} ---\n{text}")
        return "\n".join(all_text)
    
    def extract_text_with_pages(self) -> List[Tuple[int, str]]:
        """Extract text with page numbers."""
        pages_text = []
        for page_num in range(len(self.doc)):
            text = self.extract_text_by_page(page_num)
            pages_text.append((page_num + 1, text))
        return pages_text
    
    def extract_tables_from_page(self, page_num: int) -> List[List[List[str]]]:
        """Extract tables from a specific page using pdfplumber."""
        tables = []
        with pdfplumber.open(str(self.pdf_path)) as pdf:
            if page_num < 0 or page_num >= len(pdf.pages):
                raise ValueError(f"Page number {page_num} out of range")
            
            page = pdf.pages[page_num]
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
        
        return tables
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[Tuple[int, str]]:
        """Search for text across all pages.
        
        Returns list of (page_number, context) tuples.
        """
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for page_num in range(len(self.doc)):
            text = self.extract_text_by_page(page_num)
            if re.search(query, text, flags):
                # Extract context around the match
                lines = text.split('\n')
                context_lines = []
                for i, line in enumerate(lines):
                    if re.search(query, line, flags):
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = '\n'.join(lines[start:end])
                        context_lines.append(context)
                
                if context_lines:
                    results.append((page_num + 1, '\n...\n'.join(context_lines)))
        
        return results
    
    def chunk_text(self, chunk_size: int = 2000, overlap: int = 200) -> List[PDFChunk]:
        """Split PDF text into overlapping chunks for processing.
        
        Args:
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
        chunks = []
        
        for page_num in range(len(self.doc)):
            page_text = self.extract_text_by_page(page_num)
            
            # If page is smaller than chunk_size, use whole page
            if len(page_text) <= chunk_size:
                chunks.append(PDFChunk(
                    text=page_text,
                    page_number=page_num + 1,
                    start_char=0,
                    end_char=len(page_text),
                    metadata={"full_page": True}
                ))
                continue
            
            # Split page into overlapping chunks
            start = 0
            while start < len(page_text):
                end = min(start + chunk_size, len(page_text))
                chunk_text = page_text[start:end]
                
                chunks.append(PDFChunk(
                    text=chunk_text,
                    page_number=page_num + 1,
                    start_char=start,
                    end_char=end,
                    metadata={"full_page": False}
                ))
                
                # Move to next chunk with overlap
                if end >= len(page_text):
                    break
                start = end - overlap
        
        return chunks
    
    def get_page_range_text(self, start_page: int, end_page: int) -> str:
        """Extract text from a range of pages.
        
        Args:
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed, inclusive)
        """
        if start_page < 1 or end_page > len(self.doc):
            raise ValueError("Page range out of bounds")
        
        text_parts = []
        for page_num in range(start_page - 1, end_page):
            text = self.extract_text_by_page(page_num)
            text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")
        
        return "\n".join(text_parts)
    
    def extract_section_by_keywords(self, keywords: List[str], context_pages: int = 2) -> List[Tuple[int, str]]:
        """Find sections containing specific keywords and extract with context.
        
        Args:
            keywords: List of keywords to search for
            context_pages: Number of pages before and after to include
        """
        relevant_pages = set()
        
        # Find all pages containing any keyword
        for keyword in keywords:
            matches = self.search_text(keyword, case_sensitive=False)
            for page_num, _ in matches:
                # Add the page and context pages
                for p in range(max(1, page_num - context_pages),
                             min(len(self.doc) + 1, page_num + context_pages + 1)):
                    relevant_pages.add(p)
        
        # Extract text from relevant pages
        results = []
        for page_num in sorted(relevant_pages):
            text = self.extract_text_by_page(page_num - 1)
            results.append((page_num, text))
        
        return results
    
    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class TableExtractor:
    """Specialized class for extracting tables from PDFs."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def extract_all_tables(self) -> Dict[int, List[List[List[str]]]]:
        """Extract all tables from PDF, organized by page.
        
        Returns:
            Dictionary mapping page numbers to lists of tables
        """
        all_tables = {}
        
        with pdfplumber.open(str(self.pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    all_tables[page_num + 1] = tables
        
        return all_tables
    
    def find_table_by_header(self, header_keywords: List[str]) -> List[Tuple[int, List[List[str]]]]:
        """Find tables containing specific header keywords.
        
        Returns:
            List of (page_number, table) tuples
        """
        matching_tables = []
        
        with pdfplumber.open(str(self.pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                
                for table in tables:
                    if not table or not table[0]:  # Empty table
                        continue
                    
                    # Check if any keyword in first row (header)
                    header_row = ' '.join(str(cell) for cell in table[0] if cell)
                    if any(keyword.lower() in header_row.lower() for keyword in header_keywords):
                        matching_tables.append((page_num + 1, table))
        
        return matching_tables


def extract_numeric_value(text: str) -> Optional[float]:
    """Extract numeric value from text string.
    
    Handles formats like:
    - 1,234,567
    - 1.234.567 (European format)
    - 1 234 567 (space separator)
    - 12.5%
    - €1,234.56
    """
    if not text:
        return None
    
    # Remove currency symbols and common prefixes
    text = re.sub(r'[€$£¥]', '', text)
    
    # Handle percentages
    is_percentage = '%' in text
    text = text.replace('%', '')
    
    # Remove spaces
    text = text.strip().replace(' ', '')
    
    # Try to detect format and clean
    # If has both comma and dot, determine which is decimal separator
    if ',' in text and '.' in text:
        # If dot comes after comma, it's decimal separator
        if text.rindex('.') > text.rindex(','):
            text = text.replace(',', '')
        else:
            text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        # Check if comma is thousands or decimal separator
        # If after comma there are exactly 3 digits followed by comma or end, it's thousands
        if re.match(r'^[\d,]+,\d{3}($|,)', text):
            text = text.replace(',', '')
        else:
            text = text.replace(',', '.')
    
    try:
        value = float(text)
        if is_percentage and value > 1:
            value = value / 100
        return value
    except ValueError:
        return None
