"""
Document Processing and Chunking for Knowledge Ingestion Pipeline
Handles document parsing, cleaning, and chunking strategies
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, field

from knowledge.config import get_config

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


@dataclass
class Chunk:
    """Represents a document chunk"""
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """Result of document processing"""
    title: str
    content: str
    content_type: str
    language: str
    metadata: Dict
    chunks: List[Chunk]


class TextCleaner:
    """Utilities for cleaning and normalizing text"""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace while preserving paragraph structure"""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize line breaks (but preserve paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace from lines
        text = re.sub(r' +\n', '\n', text)
        return text.strip()

    @staticmethod
    def remove_control_chars(text: str) -> str:
        """Remove control characters except newlines and tabs"""
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    @staticmethod
    def clean_for_embedding(text: str) -> str:
        """Clean text for embedding generation"""
        text = TextCleaner.remove_control_chars(text)
        text = TextCleaner.normalize_whitespace(text)
        # Remove excessive punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        return text

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Average English word is ~4 chars, average token is ~4 chars
        # This is a rough estimate; actual tokenization varies by model
        return len(text) // 4


class DocumentProcessor:
    """Main document processor for parsing and chunking"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        strategy: ChunkingStrategy = None,
    ):
        config = get_config()
        self.chunk_size = chunk_size or config.chunking.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunking.chunk_overlap
        self.strategy = strategy or ChunkingStrategy(config.chunking.strategy)
        self.cleaner = TextCleaner()

    def process(
        self,
        content: str,
        title: str = "Untitled",
        content_type: str = "text/plain",
        language: str = "en",
        metadata: Dict = None,
    ) -> ProcessedDocument:
        """
        Process a document: clean, analyze, and chunk.
        """
        # Clean the content
        cleaned_content = self.cleaner.clean_for_embedding(content)

        # Choose chunking strategy
        if self.strategy == ChunkingStrategy.FIXED:
            chunks = self._chunk_fixed(cleaned_content)
        elif self.strategy == ChunkingStrategy.RECURSIVE:
            chunks = self._chunk_recursive(cleaned_content)
        elif self.strategy == ChunkingStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(cleaned_content)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(cleaned_content)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            # Semantic chunking requires embeddings - fall back to recursive
            logger.warning("Semantic chunking not implemented, using recursive")
            chunks = self._chunk_recursive(cleaned_content)
        else:
            chunks = self._chunk_recursive(cleaned_content)

        return ProcessedDocument(
            title=title,
            content=cleaned_content,
            content_type=content_type,
            language=language,
            metadata=metadata or {},
            chunks=chunks,
        )

    def _chunk_fixed(self, text: str) -> List[Chunk]:
        """Fixed-size chunking with overlap"""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to break at word boundary
            if end < len(text):
                # Look for space within last 50 chars
                space_pos = text.rfind(' ', end - 50, end)
                if space_pos > start:
                    end = space_pos

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(Chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    token_count=self.cleaner.estimate_tokens(chunk_text),
                ))
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start <= chunks[-1].start_char if chunks else 0:
                start = end  # Prevent infinite loop

        return chunks

    def _chunk_recursive(self, text: str) -> List[Chunk]:
        """
        Recursive chunking that respects document structure.
        Splits by paragraphs first, then sentences, then words.
        """
        # Define separators in order of preference
        separators = [
            "\n\n",      # Paragraph breaks
            "\n",        # Line breaks
            ". ",        # Sentences
            "! ",        # Exclamations
            "? ",        # Questions
            "; ",        # Semicolons
            ", ",        # Commas
            " ",         # Words
        ]

        chunks = []
        self._recursive_split(text, separators, 0, chunks, 0)
        return chunks

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        sep_index: int,
        chunks: List[Chunk],
        global_offset: int,
    ) -> int:
        """Recursively split text using separators"""
        if not text.strip():
            return len(chunks)

        # If text is small enough, add as chunk
        if len(text) <= self.chunk_size:
            text = text.strip()
            if text:
                chunks.append(Chunk(
                    content=text,
                    chunk_index=len(chunks),
                    start_char=global_offset,
                    end_char=global_offset + len(text),
                    token_count=self.cleaner.estimate_tokens(text),
                ))
            return len(chunks)

        # If no more separators, force split
        if sep_index >= len(separators):
            return self._force_split(text, chunks, global_offset)

        separator = separators[sep_index]
        parts = text.split(separator)

        current_chunk = ""
        current_offset = global_offset

        for i, part in enumerate(parts):
            # Add separator back (except for last part)
            if i < len(parts) - 1:
                part_with_sep = part + separator
            else:
                part_with_sep = part

            # Check if adding this part exceeds chunk size
            if len(current_chunk) + len(part_with_sep) <= self.chunk_size:
                current_chunk += part_with_sep
            else:
                # Save current chunk if not empty
                if current_chunk.strip():
                    if len(current_chunk) <= self.chunk_size:
                        chunks.append(Chunk(
                            content=current_chunk.strip(),
                            chunk_index=len(chunks),
                            start_char=current_offset,
                            end_char=current_offset + len(current_chunk),
                            token_count=self.cleaner.estimate_tokens(current_chunk),
                        ))
                    else:
                        # Recursively split with next separator
                        self._recursive_split(
                            current_chunk, separators, sep_index + 1,
                            chunks, current_offset
                        )

                current_offset = current_offset + len(current_chunk)
                current_chunk = part_with_sep

        # Handle remaining content
        if current_chunk.strip():
            if len(current_chunk) <= self.chunk_size:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=len(chunks),
                    start_char=current_offset,
                    end_char=current_offset + len(current_chunk),
                    token_count=self.cleaner.estimate_tokens(current_chunk),
                ))
            else:
                self._recursive_split(
                    current_chunk, separators, sep_index + 1,
                    chunks, current_offset
                )

        return len(chunks)

    def _force_split(
        self,
        text: str,
        chunks: List[Chunk],
        global_offset: int,
    ) -> int:
        """Force split when no separators work"""
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(Chunk(
                    content=chunk_text,
                    chunk_index=len(chunks),
                    start_char=global_offset + start,
                    end_char=global_offset + end,
                    token_count=self.cleaner.estimate_tokens(chunk_text),
                ))
            start = end - self.chunk_overlap
            if start <= 0:
                start = end
        return len(chunks)

    def _chunk_by_sentence(self, text: str) -> List[Chunk]:
        """Chunk by sentences, combining until chunk_size reached"""
        # Simple sentence splitting (could use NLTK/spaCy for better results)
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)

        chunks = []
        current_chunk = ""
        current_start = 0
        offset = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                    current_start = offset
            else:
                if current_chunk:
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        chunk_index=len(chunks),
                        start_char=current_start,
                        end_char=offset,
                        token_count=self.cleaner.estimate_tokens(current_chunk),
                    ))
                current_chunk = sentence
                current_start = offset

            offset += len(sentence) + 1

        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=len(chunks),
                start_char=current_start,
                end_char=offset,
                token_count=self.cleaner.estimate_tokens(current_chunk),
            ))

        return chunks

    def _chunk_by_paragraph(self, text: str) -> List[Chunk]:
        """Chunk by paragraphs, splitting large ones"""
        paragraphs = text.split('\n\n')

        chunks = []
        offset = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                offset += 2
                continue

            if len(para) <= self.chunk_size:
                chunks.append(Chunk(
                    content=para,
                    chunk_index=len(chunks),
                    start_char=offset,
                    end_char=offset + len(para),
                    token_count=self.cleaner.estimate_tokens(para),
                ))
            else:
                # Split large paragraph using recursive strategy
                sub_chunks = self._chunk_recursive(para)
                for sub in sub_chunks:
                    sub.start_char += offset
                    sub.end_char += offset
                    sub.chunk_index = len(chunks)
                    chunks.append(sub)

            offset += len(para) + 2

        return chunks

    def chunks_to_dicts(self, chunks: List[Chunk]) -> List[Dict]:
        """Convert Chunk objects to dictionaries for database storage"""
        return [
            {
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'start_char': chunk.start_char,
                'end_char': chunk.end_char,
                'token_count': chunk.token_count,
                'metadata': chunk.metadata,
            }
            for chunk in chunks
        ]


class FileParser:
    """Parse different file types to extract text content"""

    SUPPORTED_TYPES = {
        'text/plain': 'parse_text',
        'text/markdown': 'parse_markdown',
        'text/html': 'parse_html',
        'application/pdf': 'parse_pdf',
        'application/json': 'parse_json',
        'text/csv': 'parse_csv',
    }

    def parse(
        self,
        content: bytes,
        content_type: str,
        filename: str = None,
    ) -> Tuple[str, Dict]:
        """
        Parse file content and return (text, metadata).
        """
        parser_method = self.SUPPORTED_TYPES.get(content_type)
        if not parser_method:
            # Try to detect from filename
            if filename:
                content_type = self._detect_type(filename)
                parser_method = self.SUPPORTED_TYPES.get(content_type)

        if not parser_method:
            logger.warning(f"Unsupported content type: {content_type}")
            # Attempt to decode as text
            return self._try_decode(content), {}

        parser = getattr(self, parser_method)
        return parser(content)

    def _detect_type(self, filename: str) -> str:
        """Detect content type from filename"""
        ext_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.csv': 'text/csv',
        }
        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext_map.get(ext, 'text/plain')

    def _try_decode(self, content: bytes) -> str:
        """Try to decode bytes as text"""
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode('utf-8', errors='replace')

    def parse_text(self, content: bytes) -> Tuple[str, Dict]:
        """Parse plain text"""
        return self._try_decode(content), {}

    def parse_markdown(self, content: bytes) -> Tuple[str, Dict]:
        """Parse markdown - extract text content"""
        text = self._try_decode(content)
        metadata = {}

        # Extract YAML front matter if present
        if text.startswith('---'):
            parts = text.split('---', 2)
            if len(parts) >= 3:
                # Parse YAML front matter (basic)
                yaml_content = parts[1].strip()
                for line in yaml_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                text = parts[2]

        # Remove markdown formatting for cleaner embedding
        # Remove headers formatting
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove link formatting
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove image formatting
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        # Remove bold/italic
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
        # Remove code blocks (but keep content)
        text = re.sub(r'```[^\n]*\n', '', text)
        text = re.sub(r'```', '', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)

        return text, metadata

    def parse_html(self, content: bytes) -> Tuple[str, Dict]:
        """Parse HTML - extract text content"""
        try:
            from html.parser import HTMLParser
            from io import StringIO

            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = StringIO()
                    self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
                    self.current_skip = False
                    self.title = None

                def handle_starttag(self, tag, attrs):
                    if tag in self.skip_tags:
                        self.current_skip = True
                    if tag == 'title':
                        self.in_title = True

                def handle_endtag(self, tag):
                    if tag in self.skip_tags:
                        self.current_skip = False
                    if tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
                        self.text.write('\n')

                def handle_data(self, data):
                    if not self.current_skip:
                        self.text.write(data)

            parser = HTMLTextExtractor()
            parser.feed(self._try_decode(content))
            return parser.text.getvalue(), {}

        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
            # Fallback: strip tags with regex
            text = self._try_decode(content)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            return text, {}

    def parse_pdf(self, content: bytes) -> Tuple[str, Dict]:
        """Parse PDF - requires PyPDF2 or pdfplumber"""
        try:
            import io
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text_parts.append(page.extract_text() or '')
                    metadata = pdf.metadata or {}
                    return '\n\n'.join(text_parts), metadata
            except ImportError:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or '')
                metadata = dict(reader.metadata) if reader.metadata else {}
                return '\n\n'.join(text_parts), metadata

        except ImportError:
            logger.error("PDF parsing requires pdfplumber or PyPDF2")
            return "", {"error": "PDF parsing not available"}
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return "", {"error": str(e)}

    def parse_json(self, content: bytes) -> Tuple[str, Dict]:
        """Parse JSON - extract text fields"""
        import json
        try:
            data = json.loads(self._try_decode(content))
            text_parts = []
            self._extract_json_text(data, text_parts)
            return '\n'.join(text_parts), {"source_type": "json"}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return "", {"error": str(e)}

    def _extract_json_text(self, data, parts: List[str], prefix: str = ""):
        """Recursively extract text from JSON structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                self._extract_json_text(value, parts, f"{prefix}{key}: ")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._extract_json_text(item, parts, f"{prefix}[{i}] ")
        elif isinstance(data, str) and len(data) > 10:
            parts.append(f"{prefix}{data}")

    def parse_csv(self, content: bytes) -> Tuple[str, Dict]:
        """Parse CSV - convert to text representation"""
        import csv
        import io

        text = self._try_decode(content)
        reader = csv.reader(io.StringIO(text))

        rows = list(reader)
        if not rows:
            return "", {}

        # Use first row as headers
        headers = rows[0]
        text_parts = []

        for row in rows[1:]:
            row_text = "; ".join(
                f"{h}: {v}" for h, v in zip(headers, row) if v.strip()
            )
            if row_text:
                text_parts.append(row_text)

        return '\n'.join(text_parts), {
            "source_type": "csv",
            "columns": headers,
            "row_count": len(rows) - 1,
        }
