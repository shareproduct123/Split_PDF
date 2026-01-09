"""
PDF Labor Agreement Splitter - Final Version
Balanced approach for splitting French labor agreements
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgreementSplitter:
    """Intelligent PDF splitter for French labor agreements"""
    
    # Section detection patterns with priorities
    PATTERNS = {
        'TOC': [
            (r'^TABLE\s+DES\s+MATI[EÈ]RES', 100),
            (r'^SOMMAIRE\s*$', 95),
        ],
        'Lettres_Entente': [
            (r'^LETTRE[S]?\s+D[\'\']ENTENTE\s+N[O°]?\s*\d+', 100),
            (r'^LETTRE[S]?\s+D[\'\']ENTENTE', 95),
            (r'^M[ÉE]MORANDU?M', 90),
        ],
        'Annexe': [
            (r'^ANNEXE\s+[A-Z]\s*[-–—:]', 100),
            (r'^ANNEXE\s+[IVX]+\s*[-–—:]', 100),
            (r'^ANNEXE\s+\d+\s*[-–—:]', 100),
            (r'^\d+\s+\d+ANNEXE\s+[A-Z]', 95),  # Page number + ANNEXE
        ],
        'Articles': [
            (r'^CHAPITRE\s+[IVX\d]+\s*[-–—:]', 95),
            (r'^SECTION\s+[IVX\d]+\s*[-–—:]', 95),
        ],
        'Signatures': [
            (r'^SIGNATURES?\s*$', 90),
            (r'^EN\s+FOI\s+DE\s+QUOI', 85),
        ],
    }
    
    def __init__(self, input_pdf: str, output_dir: str = None, 
                 min_pages: int = 2, merge_threshold: int = 5):
        """
        Initialize the splitter
        
        Args:
            input_pdf: Input PDF path
            output_dir: Output directory
            min_pages: Minimum pages for a section
            merge_threshold: Max pages gap to merge same section types
        """
        self.input_pdf = Path(input_pdf)
        
        if not self.input_pdf.exists():
            raise FileNotFoundError(f"File not found: {input_pdf}")
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.input_pdf.parent / f"{self.input_pdf.stem}_split"
        
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.min_pages = min_pages
        self.merge_threshold = merge_threshold
        self.reader = None
        
    def extract_text(self, page) -> str:
        """Extract text from page"""
        try:
            return page.extract_text() or ""
        except Exception as e:
            logger.debug(f"Text extraction error: {e}")
            return ""
    
    def get_key_lines(self, text: str, max_lines: int = 5) -> List[str]:
        """Get first significant lines from text"""
        lines = []
        for line in text.split('\n'):
            cleaned = line.strip()
            # Skip empty, pure numbers, or very short lines
            if cleaned and not cleaned.isdigit() and len(cleaned) > 2:
                lines.append(cleaned)
                if len(lines) >= max_lines:
                    break
        return lines
    
    def detect_section(self, text: str, page_num: int) -> Optional[Tuple[str, int, str]]:
        """
        Detect section type from page text
        
        Returns:
            (section_type, confidence, matched_line) or None
        """
        lines = self.get_key_lines(text, 3)
        
        if not lines:
            return None
        
        # Check first 2 lines
        for line_idx, line in enumerate(lines[:2]):
            line_upper = line.upper()
            
            # Try each section type
            for section_type, patterns in self.PATTERNS.items():
                for pattern, base_confidence in patterns:
                    if re.search(pattern, line_upper):
                        # Reduce confidence if not in first line
                        confidence = base_confidence if line_idx == 0 else base_confidence - 10
                        logger.debug(f"P{page_num + 1}: '{section_type}' - {line[:50]}")
                        return (section_type, confidence, line[:80])
        
        return None
    
    def find_all_sections(self) -> List[Dict]:
        """Find all section markers in the document"""
        self.reader = PdfReader(self.input_pdf)
        total_pages = len(self.reader.pages)
        
        logger.info(f"Scanning: {self.input_pdf.name} ({total_pages} pages)")
        
        sections = []
        
        for page_num in range(total_pages):
            text = self.extract_text(self.reader.pages[page_num])
            detection = self.detect_section(text, page_num)
            
            if detection:
                section_type, confidence, header = detection
                
                # Only accept high-confidence detections
                if confidence >= 80:
                    sections.append({
                        'type': section_type,
                        'page': page_num,
                        'confidence': confidence,
                        'header': header
                    })
                    logger.info(f"Page {page_num + 1}: {section_type}")
        
        return sections
    
    def build_sections(self, markers: List[Dict]) -> List[Dict]:
        """Build section ranges from markers"""
        if not markers:
            total_pages = len(self.reader.pages)
            return [{
                'type': 'Complete_Agreement',
                'start_page': 0,
                'end_page': total_pages - 1,
                'confidence': 50,
                'header': 'Full document'
            }]
        
        sections = []
        total_pages = len(self.reader.pages)
        
        # Create sections from markers
        for i, marker in enumerate(markers):
            start = marker['page']
            end = markers[i + 1]['page'] - 1 if i + 1 < len(markers) else total_pages - 1
            
            sections.append({
                'type': marker['type'],
                'start_page': start,
                'end_page': end,
                'confidence': marker['confidence'],
                'header': marker['header']
            })
        
        # Merge similar adjacent sections
        sections = self.merge_sections(sections)
        
        return sections
    
    def merge_sections(self, sections: List[Dict]) -> List[Dict]:
        """Merge adjacent sections of the same type"""
        if len(sections) <= 1:
            return sections
        
        merged = []
        current = sections[0].copy()
        
        for next_sec in sections[1:]:
            gap = next_sec['start_page'] - current['end_page']
            
            # Merge if same type and close enough
            if current['type'] == next_sec['type'] and gap <= self.merge_threshold:
                current['end_page'] = next_sec['end_page']
                current['confidence'] = max(current['confidence'], next_sec['confidence'])
                logger.debug(f"Merged {current['type']} sections")
            else:
                merged.append(current)
                current = next_sec.copy()
        
        merged.append(current)
        return merged
    
    def create_report(self, sections: List[Dict]) -> str:
        """Generate analysis report"""
        report = f"Document Analysis: {self.input_pdf.name}\n"
        report += "=" * 80 + "\n\n"
        report += f"Total pages: {len(self.reader.pages)}\n"
        report += f"Sections found: {len(sections)}\n\n"
        
        for idx, sec in enumerate(sections, 1):
            pages = sec['end_page'] - sec['start_page'] + 1
            report += f"{idx}. {sec['type']}\n"
            report += f"   Pages: {sec['start_page'] + 1}-{sec['end_page'] + 1} ({pages} pages)\n"
            report += f"   Confidence: {sec['confidence']}%\n"
            if 'header' in sec:
                report += f"   Header: {sec['header']}\n"
            report += "\n"
        
        return report
    
    def split_pdf(self, sections: List[Dict]) -> List[str]:
        """Split PDF into files"""
        created = []
        counters = {}
        
        for sec in sections:
            start = sec['start_page']
            end = sec['end_page']
            pages = end - start + 1
            stype = sec['type']
            
            if pages < self.min_pages:
                logger.info(f"Skipping {stype}: only {pages} page(s)")
                continue
            
            # Track count per type
            counters[stype] = counters.get(stype, 0) + 1
            num = counters[stype]
            
            # Create PDF
            writer = PdfWriter()
            for p in range(start, end + 1):
                writer.add_page(self.reader.pages[p])
            
            # Filename
            if counters[stype] > 1:
                filename = f"{stype}_{num:02d}_p{start + 1}-{end + 1}.pdf"
            else:
                filename = f"{stype}_p{start + 1}-{end + 1}.pdf"
            
            filepath = self.output_dir / filename
            
            try:
                with open(filepath, 'wb') as f:
                    writer.write(f)
                logger.info(f"Created: {filename} ({pages} pages)")
                created.append(str(filepath))
            except Exception as e:
                logger.error(f"Error creating {filename}: {e}")
        
        return created
    
    def process(self) -> Dict:
        """Main processing function"""
        try:
            # Find sections
            markers = self.find_all_sections()
            sections = self.build_sections(markers)
            
            # Create report
            report = self.create_report(sections)
            report_path = self.output_dir / "analysis_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved: {report_path.name}")
            
            # Split PDF
            files = self.split_pdf(sections)
            
            return {
                'success': True,
                'input_file': str(self.input_pdf),
                'output_dir': str(self.output_dir),
                'sections_found': len(sections),
                'files_created': len(files),
                'created_files': files,
                'report_path': str(report_path)
            }
        
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'input_file': str(self.input_pdf)
            }


def batch_process(input_dir: str, output_dir: str = None, 
                  min_pages: int = 2, merge_threshold: int = 5):
    """Process multiple PDFs"""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        logger.error(f"Directory not found: {input_dir}")
        return []
    
    pdfs = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))
    
    if not pdfs:
        logger.warning(f"No PDFs found in {input_dir}")
        return []
    
    logger.info(f"Found {len(pdfs)} PDF(s)\n")
    
    results = []
    
    for pdf in pdfs:
        logger.info(f"{'=' * 80}")
        logger.info(f"Processing: {pdf.name}")
        logger.info(f"{'=' * 80}")
        
        try:
            out = Path(output_dir) / f"{pdf.stem}_split" if output_dir else None
            splitter = AgreementSplitter(
                str(pdf), 
                str(out) if out else None,
                min_pages,
                merge_threshold
            )
            result = splitter.process()
            results.append(result)
        except Exception as e:
            logger.error(f"Failed: {e}")
            results.append({
                'success': False,
                'input_file': str(pdf),
                'error': str(e)
            })
        
        print()  # Blank line between files
    
    # Summary
    logger.info(f"{'=' * 80}")
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info(f"{'=' * 80}")
    
    success = sum(1 for r in results if r.get('success'))
    total_files = sum(r.get('files_created', 0) for r in results)
    
    logger.info(f"PDFs processed: {len(results)}")
    logger.info(f"Successful: {success}")
    logger.info(f"Failed: {len(results) - success}")
    logger.info(f"Total files created: {total_files}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Split French labor agreement PDFs into sections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file
  python split_agreement.py agreement.pdf
  
  # Batch processing
  python split_agreement.py -b ./Agreements
  
  # Custom settings
  python split_agreement.py agreement.pdf --min-pages 3 --merge-gap 10
  
  # Verbose mode
  python split_agreement.py -b ./Agreements -v
        """
    )
    
    parser.add_argument('input', help='PDF file or directory (with -b)')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-b', '--batch', action='store_true', help='Batch mode')
    parser.add_argument('--min-pages', type=int, default=2,
                        help='Minimum pages per section (default: 2)')
    parser.add_argument('--merge-gap', type=int, default=5,
                        help='Max page gap to merge sections (default: 5)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if args.batch:
        batch_process(args.input, args.output, args.min_pages, args.merge_gap)
    else:
        splitter = AgreementSplitter(args.input, args.output, args.min_pages, args.merge_gap)
        result = splitter.process()
        
        if result['success']:
            print(f"\n✓ Success! Created {result['files_created']} file(s)")
            print(f"  Output: {result['output_dir']}")
            print(f"  Report: {result['report_path']}")
        else:
            print(f"\n✗ Failed: {result.get('error')}")
            exit(1)


if __name__ == '__main__':
    main()
