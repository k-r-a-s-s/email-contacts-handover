# Email Contact Extractor

A Python tool for extracting and analyzing contacts from Google Takeout MBOX files.

## Overview

This project helps extract valuable contact information from email archives to facilitate smooth organizational transitions. It focuses on:

- Extracting contacts from sent emails only (your outbound communications)
- Filtering for Australian government/organization contacts (.gov.au, .org.au, etc.)
- Analyzing relationship context using LLM enhancement
- Generating handover-ready contact lists for CRM import

## Project Structure

```
email-contatcs-handover/
├── email_contact_extractor.py  # Main extraction script
├── llm_enhancer.py            # LLM-powered contact analysis
├── test_extraction.py         # Test script with sample data
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

1. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Step 1: Basic Contact Extraction

Extract contacts from your Google Takeout MBOX file:

```bash
python email_contact_extractor.py --mbox path/to/your/takeout.mbox --output results
```

**Options:**
- `--mbox`: Path to your MBOX file (required)
- `--output`: Output directory (default: "output")

**Output files:**
- `contacts_all.csv` - All extracted contacts
- `contacts_australian_government.csv` - Australian government contacts only
- `contacts_summary.xlsx` - Excel file with multiple sheets and statistics
- `contact_interactions.json` - Detailed interaction history
- `contact_extraction_report.txt` - Summary report

### Step 2: LLM Enhancement (Optional)

Enhance contacts with AI-powered relationship analysis:

```bash
python llm_enhancer.py --output results --provider openai --max-contacts 20
```

**Prerequisites:**
- Set up API key in environment: `export OPENAI_API_KEY=your_key_here`
- Or create a `.env` file with: `OPENAI_API_KEY=your_key_here`

**Options:**
- `--output`: Directory containing extracted contacts (default: "output")
- `--provider`: LLM provider - "openai" or "anthropic" (default: "openai")
- `--max-contacts`: Limit number of contacts to analyze (for testing/cost control)

**Additional output files:**
- `contacts_enhanced.csv` - Contacts with LLM analysis
- `contacts_enhanced.xlsx` - Excel with priority-based sheets
- `enhancement_report.txt` - LLM analysis summary

## Testing

Run the test script to verify everything works:

```bash
python test_extraction.py
```

This creates sample emails and tests the extraction pipeline.

## Key Features

### Contact Filtering

- **Sent emails only**: Focuses on your outbound communications
- **External contacts only**: Excludes internal ALLFED emails
- **Australian focus**: Prioritizes .gov.au, .org.au, .edu.au domains
- **Deduplication**: Combines multiple interactions per contact

### Data Extraction

- Contact name and email
- Organization (extracted from signatures/domains)
- Interaction frequency and dates
- Email subjects and content samples
- Domain classification

### LLM Enhancement

The LLM enhancement provides:

- **Relationship Type**: Government Official, Academic, NGO, etc.
- **Engagement Level**: High/Medium/Low based on interaction patterns
- **Key Topics**: Main discussion themes
- **Relationship Description**: Context about the person's role
- **Handover Priority**: Importance for successor relationships
- **Next Steps**: Suggestions for maintaining relationships

## Configuration

### Internal Domains

Edit `email_contact_extractor.py` to customize internal domains:

```python
self.internal_domains = {
    'allfed.info', 'allfed.org', 'allfed.net'
    # Add your organization's domains here
}
```

### Australian Government Domains

Customize the domain patterns in `email_contact_extractor.py`:

```python
self.au_gov_domains = {
    '.gov.au', '.org.au', '.edu.au', '.asn.au', '.id.au'
}
```

### LLM Configuration

- **OpenAI**: Uses GPT-4o-mini for cost efficiency
- **Anthropic**: Uses Claude-3-haiku for cost efficiency
- Cost is typically $0.01-0.05 per contact analyzed

## Output Formats

### CSV Files
- Compatible with most CRM systems
- Includes all contact data and analysis
- Sorted by priority and engagement level

### Excel Files
- Multiple sheets for different priority levels
- Summary statistics
- Formatted for easy review

### Reports
- Human-readable summaries
- Key statistics and breakdowns
- Ready for handover documentation

## Privacy and Security

- **Local processing**: All email content stays on your machine
- **API calls**: Only contact summaries sent to LLM (if using enhancement)
- **No storage**: LLM providers configured not to store data
- **Sensitive data**: Consider reviewing emails before LLM processing

## Troubleshooting

### Common Issues

1. **MBOX file not found**
   - Ensure the path to your Google Takeout MBOX file is correct
   - File should have `.mbox` extension

2. **No contacts found**
   - Check that emails are from ALLFED domains
   - Verify the MBOX contains sent emails (not just received)
   - Review internal domain configuration

3. **LLM API errors**
   - Verify API key is set correctly
   - Check internet connection
   - Ensure you have API credits/quota

4. **Memory issues with large MBOX files**
   - Consider processing in chunks
   - Close other applications
   - Use `--max-contacts` for testing

### Getting Help

1. Run the test script first: `python test_extraction.py`
2. Check the generated reports for processing statistics
3. Review error messages in the console output

## Cost Estimation

### LLM Enhancement Costs (approximate)
- OpenAI GPT-4o-mini: ~$0.01-0.02 per contact
- Anthropic Claude-3-haiku: ~$0.01-0.03 per contact
- 100 contacts ≈ $1-3 in API costs

### Processing Time
- Extraction: ~1-10 minutes per 1000 emails
- LLM enhancement: ~30-60 seconds per contact

## Next Steps

After running the extraction:

1. **Review the reports** to understand your contact network
2. **Check high-priority contacts** for handover planning
3. **Import to CRM** using the CSV files
4. **Update contact info** with current details if needed
5. **Plan transition meetings** based on relationship priority

## Contributing

This tool was designed for ALLFED's specific handover needs but can be adapted for other organizations. Key customization points:

- Internal domain configuration
- Target domain patterns (not just Australian government)
- LLM prompts for different organizational contexts
- Output format requirements
