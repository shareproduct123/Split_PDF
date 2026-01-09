# Customization Guide

## Adding Custom Section Patterns

If your labor agreements use different terminology or structure, you can easily add custom patterns.

### Pattern Structure

Patterns are defined in `split_agreement.py` in the `PATTERNS` dictionary:

```python
PATTERNS = {
    'Section_Type_Name': [
        (r'REGEX_PATTERN', confidence_score),
        (r'ALTERNATIVE_PATTERN', confidence_score),
    ],
}
```

- **Section_Type_Name**: Used in output filename
- **REGEX_PATTERN**: Python regex to match section header
- **confidence_score**: 1-100, higher = more reliable

## Common Pattern Examples

### Example 1: Add "Protocole" Section

```python
'Protocole': [
    (r'^PROTOCOLE\s+D[\'\']ENTENTE', 95),
    (r'^PROTOCOLE\s+N[O°]?\s*\d+', 90),
    (r'^PROTOCOLE\s+[A-Z]', 85),
],
```

### Example 2: Add "Index" Section

```python
'Index': [
    (r'^INDEX\s+ALPHAB[ÉE]TIQUE', 100),
    (r'^INDEX\s*$', 95),
],
```

### Example 3: Add "Glossaire" Section

```python
'Glossaire': [
    (r'^GLOSSAIRE\s+DES\s+TERMES', 95),
    (r'^D[ÉE]FINITIONS', 90),
    (r'^LEXIQUE', 85),
],
```

### Example 4: Add Numbered Chapters

```python
'Chapitre': [
    (r'^CHAPITRE\s+\d+\s*[-–:]', 95),
    (r'^CHAPITRE\s+[IVX]+\s*[-–:]', 95),
    (r'^TITRE\s+[IVX]+', 90),
],
```

### Example 5: Add "Préambule" Section

```python
'Preambule': [
    (r'^PR[ÉE]AMBULE', 95),
    (r'^ATTENDU\s+QUE', 85),
    (r'^CONSID[ÉE]RANT', 85),
],
```

## Regex Basics for Patterns

### Common Regex Elements:

```
^           Start of line
$           End of line
\s          Whitespace (space, tab)
\d          Digit (0-9)
[A-Z]       Any uppercase letter
[0-9]       Any digit
+           One or more
*           Zero or more
[-–:]       Match dash, en-dash, or colon
[ÉE]        Match É or E (accent variants)
[\'\']      Match apostrophe variants
```

### Pattern Examples:

```python
# Match "ANNEXE A" or "ANNEXE B"
r'^ANNEXE\s+[A-Z]\s*[-–:]'

# Match "ARTICLE 1" or "ARTICLE 99"
r'^ARTICLE\s+\d+'

# Match "CHAPITRE I" or "CHAPITRE X"
r'^CHAPITRE\s+[IVX]+'

# Match variations: MÉMORANDUM or MEMORANDUM
r'^M[ÉE]MORANDU?M'
```

## Full Example: Adding Custom Sections

Edit `split_agreement.py`, find the `PATTERNS` dictionary (around line 30), and add your sections:

```python
PATTERNS = {
    # Existing patterns
    'TOC': [
        (r'^TABLE\s+DES\s+MATI[EÈ]RES', 100),
        (r'^SOMMAIRE\s*$', 95),
    ],
    
    # Your custom additions
    'Preambule': [
        (r'^PR[ÉE]AMBULE', 95),
        (r'^ATTENDU\s+QUE', 85),
    ],
    
    'Protocole': [
        (r'^PROTOCOLE\s+D[\'\']ENTENTE', 95),
        (r'^PROTOCOLE\s+N[O°]?\s*\d+', 90),
    ],
    
    'Index': [
        (r'^INDEX\s+ALPHAB[ÉE]TIQUE', 100),
        (r'^INDEX\s*$', 95),
    ],
    
    'Glossaire': [
        (r'^GLOSSAIRE', 95),
        (r'^D[ÉE]FINITIONS', 90),
    ],
    
    # Keep existing patterns
    'Lettres_Entente': [
        (r'^LETTRE[S]?\s+D[\'\']ENTENTE\s+N[O°]?\s*\d+', 100),
        # ...
    ],
    # ... rest of patterns
}
```

## Testing Your Patterns

### Method 1: Verbose Mode

Run with `-v` flag to see what patterns match:

```bash
python split_agreement.py agreement.pdf -v
```

Look for lines like:
```
DEBUG: P5: Detected 'Protocole' - PROTOCOLE D'ENTENTE NO 1
```

### Method 2: Test on Sample Files

Create a test file with just the section headers you want to match, then process it.

### Method 3: Python Interactive Testing

```python
import re

# Your pattern
pattern = r'^PROTOCOLE\s+D[\'\']ENTENTE'

# Test text
test_text = "PROTOCOLE D'ENTENTE NO 1"

# Test match
if re.search(pattern, test_text, re.IGNORECASE):
    print("Match!")
else:
    print("No match")
```

## Common Issues and Solutions

### Issue: Pattern Not Matching

**Problem:** Section not being detected

**Solutions:**
1. Check if text is exactly as expected (use `-v` mode)
2. Try simpler pattern: `r'^YOUR_TEXT'`
3. Add accent variations: `[ÉE]`, `[ÀA]`, etc.
4. Make pattern more flexible with `\s+` instead of spaces

### Issue: Too Many False Positives

**Problem:** Pattern matching wrong sections

**Solutions:**
1. Make pattern more specific
2. Add anchors: `^` for start of line, `$` for end
3. Increase confidence score
4. Add more context: `r'^ANNEXE\s+[A-Z]\s*[-–:]'` instead of just `r'ANNEXE'`

### Issue: Sections Not Merging

**Problem:** Getting too many small files

**Solutions:**
1. Increase `--merge-gap`: `--merge-gap 10`
2. Check if section types are named consistently
3. Ensure confidence scores are high enough (>80)

## Advanced: Language Support

To add support for English or other languages:

```python
# Add to PATTERNS
'Appendices': [  # English
    (r'^APPENDIX\s+[A-Z]', 95),
    (r'^ANNEX\s+[A-Z]', 95),
],

'Memorandum': [  # English
    (r'^MEMORANDUM\s+OF\s+UNDERSTANDING', 95),
    (r'^MOU\s+N[O°]?\s*\d+', 90),
],

'Anexos': [  # Spanish
    (r'^ANEXO\s+[A-Z]', 95),
    (r'^AP[ÉE]NDICE\s+[A-Z]', 95),
],
```

## Tips for Creating Good Patterns

1. **Start Specific**: Begin with very specific patterns
2. **Test Incrementally**: Add one pattern at a time
3. **Use Real Examples**: Base patterns on actual documents
4. **Consider Variations**: Accents, spacing, punctuation
5. **Balance Confidence**: Too low = false positives, too high = missed sections

## Pattern Library

Common patterns for French administrative documents:

```python
# Headers
r'^EN-T[ÊE]TE'                    # Header
r'^PIED\s+DE\s+PAGE'              # Footer

# Lists
r'^LISTE\s+DES\s+TABLEAUX'        # List of tables
r'^LISTE\s+DES\s+FIGURES'         # List of figures

# References
r'^R[ÉE]F[ÉE]RENCES'              # References
r'^BIBLIOGRAPHIE'                 # Bibliography

# Appendices types
r'^ANNEXE\s+TECHNIQUE'            # Technical appendix
r'^ANNEXE\s+FINANCI[ÈE]RE'       # Financial appendix
r'^ANNEXE\s+STATISTIQUE'          # Statistical appendix

# Administrative
r'^DISPOSITIONS\s+FINALES'        # Final provisions
r'^CLAUSE\s+DE\s+NON-RENONCIATION' # Non-waiver clause
```

## Need Help?

1. Run with `-v` to see detection details
2. Check `analysis_report.txt` for insights
3. Test patterns on simple examples first
4. Share sample documents for pattern development
