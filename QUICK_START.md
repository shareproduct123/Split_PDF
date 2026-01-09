# Quick Start Guide

## For Non-Technical Users

### Easy GUI Method (Recommended)

1. **Double-click** `gui_splitter.py` (or run `python gui_splitter.py`)

2. **For a single PDF:**
   - Click "Browse..." next to Input
   - Select your PDF file
   - Click "Process"

3. **For multiple PDFs:**
   - Check the "Batch Mode" checkbox
   - Click "Browse..." and select the folder containing PDFs
   - Click "Process"

4. **Output:**
   - A new folder will be created next to each PDF
   - Named `[original_filename]_split`
   - Contains the separated sections

### Command-Line Method

**Process one file:**
```bash
python split_agreement.py "path/to/agreement.pdf"
```

**Process all files in a folder:**
```bash
python split_agreement.py -b "path/to/folder"
```

## Common Use Cases

### Case 1: I have 100 agreements to split
```bash
# Put all PDFs in one folder (e.g., C:\Agreements)
# Run batch mode:
python split_agreement.py -b C:\Agreements

# Wait 5-10 minutes
# Check each [filename]_split folder for results
```

### Case 2: I only want major sections (skip small parts)
```bash
python split_agreement.py -b C:\Agreements --min-pages 5
```

### Case 3: I want every detected section separately
```bash
python split_agreement.py -b C:\Agreements --min-pages 1 --merge-gap 1
```

### Case 4: I want to see what's happening
```bash
python split_agreement.py agreement.pdf -v
```

## Understanding the Output

After processing `agreement.pdf`, you'll find:

```
agreement_split/
├── analysis_report.txt          ← Summary of what was found
├── TOC_p1-15.pdf               ← Table of contents
├── Articles_p16-120.pdf        ← Main agreement articles
├── Annexe_01_p121-135.pdf      ← First appendix
├── Annexe_02_p136-150.pdf      ← Second appendix
└── Lettres_Entente_p151-165.pdf ← MOUs
```

**analysis_report.txt** tells you:
- How many sections were found
- Which pages belong to which section
- Confidence level of detection

## Troubleshooting

**"No sections detected"**
- Your PDF might be scanned images
- Try opening the PDF and see if you can select/copy text
- If not, you need to OCR it first

**"Too many small files"**
- Use: `--min-pages 3` to skip small sections

**"Everything in one file"**
- Your PDF might not have standard section headers
- Check the analysis report to see what was detected
- Add `-v` flag to see detailed detection logs

**"Some sections missing"**
- Lower the merge gap: `--merge-gap 2`
- Lower minimum pages: `--min-pages 1`

## Tips

1. **Test with one file first** before batch processing
2. **Check the analysis report** to understand what was detected
3. **Adjust settings** based on your specific agreements
4. **Keep original files** - this tool never modifies them

## Getting Help

Run with `-v` flag to see detailed information:
```bash
python split_agreement.py agreement.pdf -v
```

This shows you exactly what patterns are being matched and where.
