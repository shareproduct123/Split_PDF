"""
PDF Labor Agreement Splitter
Splits French labor agreements into constituent parts:
- Table des matières (TOC)
- Articles
- Annexes (Appendices)
- Lettres d'entente (MOU)
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFSplitter:
    """Splits French labor agreement PDFs into sections"""
    
    # Common section headers in French labor agreements
    SECTION_PATTERNS = [
        # Table of Contents
        (r'TABLE\s+DES\s+MATI[EÈ]RES', 'TOC'),
        (r'SOMMAIRE', 'TOC'),
        
        # Articles section
        (r'ARTICLES?', 'Articles'),
        (r'CHAPITRE\s+\d+', 'Articles'),
        (r'^ARTICLE\s+\d+', 'Articles'),
        
        # Appendices
        (r'ANNEXES?', 'Annexe'),
        (r'APPENDICES?', 'Annexe'),
        
        # Lettres d'entente (MOU)
        (r'LETTRES?\s+D[\'\']ENTENTE', 'Lettre_Entente'),
        (r'LETTRE\s+D[\'\']ENTENTE\s+N[O°]?\s*\d+', 'Lettre_Entente'),
        (r'M[ÉE]MORANDU?M\s+D[\'\']ENTENTE', 'Lettre_Entente'),
        
        # Specific annexe patterns
        (r'ANNEXE\s+[A-Z\d]+', 'Annexe'),
        
        # Signature page
        (r'SIGNATURES?', 'Signatures'),
        (r'EN\s+FOI\s+DE\s+QUOI', 'Signatures'),
    ]
    
    def __init__(self, input_pdf: str, output_dir: str = None, min_pages: int = 1):
        """
        Initialize the PDF splitter
        
        Args:
            input_pdf: Path to the input PDF file
            output_dir: Directory to save split PDFs (default: same as input with _split suffix)
            min_pages: Minimum pages for a section to be saved separately
        """
        self.input_pdf = Path(input_pdf)
        
        if not self.input_pdf.exists():
            raise FileNotFoundError(f"PDF file not found: {input_pdf}")
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Create output directory next to input file
            self.output_dir = self.input_pdf.parent / f"{self.input_pdf.stem}_split"
        
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.min_pages = min_pages
        self.reader = None
        
    def extract_text_from_page(self, page) -> str:
        """Extract text from a PDF page"""
        try:
            text = page.extract_text()
            return text.upper() if text else ""
        except Exception as e:
            logger.warning(f"Error extracting text from page: {e}")
            return ""
    
    def detect_section(self, text: str) -> Optional[Tuple[str, int]]:
        """
        Detect if the text contains a section header
        
        Returns:
            Tuple of (section_type, confidence) or None
        """
        text_lines = text.split('\n')
        
        # Check first few lines for section headers
        for i, line in enumerate(text_lines[:10]):
            line = line.strip()
            if not line:
                continue
                
            for pattern, section_type in self.SECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Higher confidence if found in first 3 lines
                    confidence = 100 if i < 3 else 70
                    logger.debug(f"Detected '{section_type}' with pattern '{pattern}' in line: {line[:50]}")
                    return (section_type, confidence)
        
        return None
    
    def analyze_document_structure(self) -> List[Dict]:
        """
        Analyze the PDF and identify section boundaries
        
        Returns:
            List of sections with start/end pages
        """
        self.reader = PdfReader(self.input_pdf)
        total_pages = len(self.reader.pages)
        
        logger.info(f"Analyzing PDF: {self.input_pdf.name} ({total_pages} pages)")
        
        sections = []
        current_section = None
        
        for page_num in range(total_pages):
            text = self.extract_text_from_page(self.reader.pages[page_num])
            detection = self.detect_section(text)
            
            if detection:
                section_type, confidence = detection
                
                # Close previous section
                if current_section:
                    current_section['end_page'] = page_num - 1
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'type': section_type,
                    'start_page': page_num,
                    'end_page': None,
                    'confidence': confidence
                }
                logger.info(f"Page {page_num + 1}: Start of '{section_type}' section")
        
        # Close last section
        if current_section:
            current_section['end_page'] = total_pages - 1
            sections.append(current_section)
        
        # If no sections detected, treat entire document as one
        if not sections:
            logger.warning("No sections detected, treating entire document as 'Complete_Agreement'")
            sections.append({
                'type': 'Complete_Agreement',
                'start_page': 0,
                'end_page': total_pages - 1,
                'confidence': 50
            })
        
        return sections
    
    def split_pdf(self, sections: List[Dict]) -> List[str]:
        """
        Split the PDF according to detected sections
        
        Returns:
            List of created file paths
        """
        created_files = []
        
        for idx, section in enumerate(sections):
            start_page = section['start_page']
            end_page = section['end_page']
            num_pages = end_page - start_page + 1
            
            # Skip sections that are too small
            if num_pages < self.min_pages:
                logger.info(f"Skipping section '{section['type']}' (only {num_pages} page(s))")
                continue
            
            # Create PDF writer
            writer = PdfWriter()
            
            # Add pages to writer
            for page_num in range(start_page, end_page + 1):
                writer.add_page(self.reader.pages[page_num])
            
            # Generate output filename
            section_type = section['type']
            output_filename = f"{idx + 1:02d}_{section_type}_p{start_page + 1}-{end_page + 1}.pdf"
            output_path = self.output_dir / output_filename
            
            # Write PDF
            try:
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                logger.info(f"Created: {output_filename} ({num_pages} page(s))")
                created_files.append(str(output_path))
            
            except Exception as e:
                logger.error(f"Error creating {output_filename}: {e}")
        
        return created_files
    
    def process(self) -> Dict:
        """
        Process the PDF: analyze and split
        
        Returns:
            Dictionary with results
        """
        try:
            # Analyze structure
            sections = self.analyze_document_structure()
            
            # Split PDF
            created_files = self.split_pdf(sections)
            
            result = {
                'success': True,
                'input_file': str(self.input_pdf),
                'output_dir': str(self.output_dir),
                'sections_found': len(sections),
                'files_created': len(created_files),
                'created_files': created_files,
                'sections': sections
            }
            
            logger.info(f"Successfully processed: {len(created_files)} files created")
            return result
        
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'input_file': str(self.input_pdf)
            }


def batch_process(input_dir: str, output_base_dir: str = None, min_pages: int = 1):
    """
    Process multiple PDF files in a directory
    
    Args:
        input_dir: Directory containing PDF files
        output_base_dir: Base directory for outputs (default: same as input_dir)
        min_pages: Minimum pages for a section
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return
    
    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to process")
    
    results = []
    
    for pdf_file in pdf_files:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {pdf_file.name}")
        logger.info(f"{'=' * 80}")
        
        try:
            # Create output directory for this PDF
            if output_base_dir:
                output_dir = Path(output_base_dir) / f"{pdf_file.stem}_split"
            else:
                output_dir = None  # Will be created automatically
            
            splitter = PDFSplitter(str(pdf_file), str(output_dir) if output_dir else None, min_pages)
            result = splitter.process()
            results.append(result)
        
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {e}")
            results.append({
                'success': False,
                'input_file': str(pdf_file),
                'error': str(e)
            })
    
    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info(f"{'=' * 80}")
    
    successful = sum(1 for r in results if r.get('success'))
    failed = len(results) - successful
    total_files = sum(r.get('files_created', 0) for r in results)
    
    logger.info(f"Total PDFs processed: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total output files created: {total_files}")
    
    return results


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Split French labor agreement PDFs into sections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF
  python pdf_splitter.py agreement.pdf
  
  # Process a single PDF with custom output directory
  python pdf_splitter.py agreement.pdf -o ./output
  
  # Process all PDFs in a directory
  python pdf_splitter.py -b ./Agreements
  
  # Process with minimum page requirement
  python pdf_splitter.py agreement.pdf --min-pages 2
        """
    )
    
    parser.add_argument('input', help='Input PDF file or directory (with -b flag)')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-b', '--batch', action='store_true', 
                        help='Batch process all PDFs in input directory')
    parser.add_argument('--min-pages', type=int, default=1,
                        help='Minimum pages for a section to be saved (default: 1)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if args.batch:
        # Batch processing
        batch_process(args.input, args.output, args.min_pages)
    else:
        # Single file processing
        splitter = PDFSplitter(args.input, args.output, args.min_pages)
        result = splitter.process()
        
        if result['success']:
            print(f"\n✓ Successfully created {result['files_created']} file(s)")
            print(f"Output directory: {result['output_dir']}")
        else:
            print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")
            exit(1)


if __name__ == '__main__':
    main()
