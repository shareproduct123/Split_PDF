"""
Enhanced PDF Labor Agreement Splitter - Version 2
Improved section detection with better heuristics
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


class PDFSplitterV2:
    """Enhanced PDF splitter for French labor agreements"""
    
    # Major section patterns - stricter matching
    MAJOR_SECTION_PATTERNS = [
        # Table of Contents - must be at start of line
        (r'^TABLE\s+DES\s+MATI[EÈ]RES\s*$', 'TOC', 100),
        (r'^SOMMAIRE\s*$', 'TOC', 100),
        
        # Lettres d'entente - high priority
        (r'^LETTRE[S]?\s+D[\'\']ENTENTE', 'Lettres_Entente', 95),
        (r'^M[ÉE]MORANDU?M\s+D[\'\']ENTENTE', 'Lettres_Entente', 95),
        
        # Annexes - numbered or lettered
        (r'^ANNEXE\s+[A-Z0-9]+\s*[-:]', 'Annexe', 90),
        (r'^ANNEXE\s+[IVX]+\s*[-:]', 'Annexe', 90),
        (r'^ANNEXE\s+\d+\s*[-:]', 'Annexe', 90),
        
        # Articles - full section headers only
        (r'^CHAPITRE\s+[IVX0-9]+\s*[-:]', 'Articles', 85),
        (r'^SECTION\s+[IVX0-9]+\s*[-:]', 'Articles', 85),
        
        # Signatures
        (r'^SIGNATURES?\s*$', 'Signatures', 80),
        (r'^EN\s+FOI\s+DE\s+QUOI', 'Signatures', 80),
    ]
    
    def __init__(self, input_pdf: str, output_dir: str = None, min_pages: int = 2):
        """
        Initialize enhanced PDF splitter
        
        Args:
            input_pdf: Path to the input PDF file
            output_dir: Directory to save split PDFs
            min_pages: Minimum pages for a section (default: 2)
        """
        self.input_pdf = Path(input_pdf)
        
        if not self.input_pdf.exists():
            raise FileNotFoundError(f"PDF file not found: {input_pdf}")
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.input_pdf.parent / f"{self.input_pdf.stem}_split"
        
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.min_pages = min_pages
        self.reader = None
        
    def extract_text_from_page(self, page) -> str:
        """Extract and clean text from PDF page"""
        try:
            text = page.extract_text()
            return text if text else ""
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
            return ""
    
    def get_first_significant_lines(self, text: str, num_lines: int = 5) -> List[str]:
        """Get first non-empty lines from text"""
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.isdigit():  # Skip page numbers
                lines.append(line)
                if len(lines) >= num_lines:
                    break
        return lines
    
    def detect_major_section(self, text: str, page_num: int) -> Optional[Tuple[str, int, str]]:
        """
        Detect major section boundaries
        
        Returns:
            Tuple of (section_type, confidence, matched_text) or None
        """
        lines = self.get_first_significant_lines(text, 3)
        
        if not lines:
            return None
        
        # Check first line primarily
        first_line = lines[0].upper().strip()
        
        for pattern, section_type, confidence in self.MAJOR_SECTION_PATTERNS:
            if re.search(pattern, first_line, re.IGNORECASE | re.MULTILINE):
                logger.debug(f"P{page_num + 1}: Detected '{section_type}' - '{first_line[:60]}'")
                return (section_type, confidence, first_line)
        
        return None
    
    def merge_similar_sections(self, sections: List[Dict]) -> List[Dict]:
        """Merge consecutive sections of the same type"""
        if not sections:
            return []
        
        merged = []
        current = sections[0].copy()
        
        for next_section in sections[1:]:
            # Merge if same type and close together (within 3 pages)
            if (current['type'] == next_section['type'] and 
                next_section['start_page'] - current['end_page'] <= 3):
                # Extend current section
                current['end_page'] = next_section['end_page']
                current['confidence'] = max(current['confidence'], next_section['confidence'])
            else:
                # Save current and start new
                merged.append(current)
                current = next_section.copy()
        
        merged.append(current)
        return merged
    
    def analyze_document_structure(self) -> List[Dict]:
        """Analyze PDF and identify major section boundaries"""
        self.reader = PdfReader(self.input_pdf)
        total_pages = len(self.reader.pages)
        
        logger.info(f"Analyzing: {self.input_pdf.name} ({total_pages} pages)")
        
        detected_sections = []
        
        # Scan all pages
        for page_num in range(total_pages):
            text = self.extract_text_from_page(self.reader.pages[page_num])
            detection = self.detect_major_section(text, page_num)
            
            if detection:
                section_type, confidence, matched_text = detection
                detected_sections.append({
                    'type': section_type,
                    'start_page': page_num,
                    'end_page': page_num,
                    'confidence': confidence,
                    'header': matched_text
                })
                logger.info(f"Page {page_num + 1}: '{section_type}' section")
        
        if not detected_sections:
            logger.warning("No sections detected")
            return [{
                'type': 'Complete_Agreement',
                'start_page': 0,
                'end_page': total_pages - 1,
                'confidence': 50,
                'header': 'Full document'
            }]
        
        # Set end pages for each section
        for i in range(len(detected_sections) - 1):
            detected_sections[i]['end_page'] = detected_sections[i + 1]['start_page'] - 1
        
        detected_sections[-1]['end_page'] = total_pages - 1
        
        # Merge similar consecutive sections
        merged_sections = self.merge_similar_sections(detected_sections)
        
        logger.info(f"Found {len(merged_sections)} major sections after merging")
        return merged_sections
    
    def create_summary_report(self, sections: List[Dict]) -> str:
        """Create a text summary of detected sections"""
        report = f"PDF Analysis Report: {self.input_pdf.name}\n"
        report += "=" * 80 + "\n\n"
        
        for idx, section in enumerate(sections, 1):
            num_pages = section['end_page'] - section['start_page'] + 1
            report += f"{idx}. {section['type']}\n"
            report += f"   Pages: {section['start_page'] + 1}-{section['end_page'] + 1} ({num_pages} pages)\n"
            report += f"   Header: {section.get('header', 'N/A')[:60]}\n\n"
        
        return report
    
    def split_pdf(self, sections: List[Dict]) -> List[str]:
        """Split PDF into separate files"""
        created_files = []
        
        # Counter for each section type
        type_counters = {}
        
        for section in sections:
            start_page = section['start_page']
            end_page = section['end_page']
            num_pages = end_page - start_page + 1
            section_type = section['type']
            
            # Skip if too small
            if num_pages < self.min_pages:
                logger.info(f"Skipping '{section_type}' (only {num_pages} page(s))")
                continue
            
            # Track section type count
            type_counters[section_type] = type_counters.get(section_type, 0) + 1
            type_num = type_counters[section_type]
            
            # Create writer
            writer = PdfWriter()
            
            for page_num in range(start_page, end_page + 1):
                writer.add_page(self.reader.pages[page_num])
            
            # Generate filename
            if type_counters[section_type] > 1:
                output_filename = f"{section_type}_{type_num:02d}_p{start_page + 1}-{end_page + 1}.pdf"
            else:
                output_filename = f"{section_type}_p{start_page + 1}-{end_page + 1}.pdf"
            
            output_path = self.output_dir / output_filename
            
            try:
                with open(output_path, 'wb') as f:
                    writer.write(f)
                
                logger.info(f"Created: {output_filename} ({num_pages} pages)")
                created_files.append(str(output_path))
            
            except Exception as e:
                logger.error(f"Error creating {output_filename}: {e}")
        
        return created_files
    
    def process(self) -> Dict:
        """Process the PDF"""
        try:
            sections = self.analyze_document_structure()
            
            # Save analysis report
            report = self.create_summary_report(sections)
            report_path = self.output_dir / "analysis_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Analysis report saved to: {report_path}")
            
            # Split PDF
            created_files = self.split_pdf(sections)
            
            return {
                'success': True,
                'input_file': str(self.input_pdf),
                'output_dir': str(self.output_dir),
                'sections_found': len(sections),
                'files_created': len(created_files),
                'created_files': created_files,
                'sections': sections,
                'report_path': str(report_path)
            }
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'input_file': str(self.input_pdf)
            }


def batch_process(input_dir: str, output_base_dir: str = None, min_pages: int = 2):
    """Batch process multiple PDFs"""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        logger.error(f"Directory not found: {input_dir}")
        return
    
    pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF file(s)")
    
    results = []
    
    for pdf_file in pdf_files:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {pdf_file.name}")
        logger.info(f"{'=' * 80}")
        
        try:
            if output_base_dir:
                output_dir = Path(output_base_dir) / f"{pdf_file.stem}_split"
            else:
                output_dir = None
            
            splitter = PDFSplitterV2(str(pdf_file), str(output_dir) if output_dir else None, min_pages)
            result = splitter.process()
            results.append(result)
        
        except Exception as e:
            logger.error(f"Failed: {e}")
            results.append({
                'success': False,
                'input_file': str(pdf_file),
                'error': str(e)
            })
    
    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("BATCH SUMMARY")
    logger.info(f"{'=' * 80}")
    
    successful = sum(1 for r in results if r.get('success'))
    total_files = sum(r.get('files_created', 0) for r in results)
    
    logger.info(f"Processed: {len(results)} PDFs")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {len(results) - successful}")
    logger.info(f"Total files created: {total_files}")
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Split French labor agreement PDFs (Enhanced Version)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_splitter_v2.py agreement.pdf
  python pdf_splitter_v2.py -b ./Agreements
  python pdf_splitter_v2.py agreement.pdf --min-pages 3 -v
        """
    )
    
    parser.add_argument('input', help='Input PDF file or directory')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-b', '--batch', action='store_true', help='Batch mode')
    parser.add_argument('--min-pages', type=int, default=2,
                        help='Minimum pages per section (default: 2)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if args.batch:
        batch_process(args.input, args.output, args.min_pages)
    else:
        splitter = PDFSplitterV2(args.input, args.output, args.min_pages)
        result = splitter.process()
        
        if result['success']:
            print(f"\n✓ Created {result['files_created']} file(s)")
            print(f"Output: {result['output_dir']}")
            print(f"Report: {result['report_path']}")
        else:
            print(f"\n✗ Failed: {result.get('error')}")
            exit(1)


if __name__ == '__main__':
    main()
