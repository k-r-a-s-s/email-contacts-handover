#!/usr/bin/env python3
"""
Test script for email contact extraction
Creates a small sample MBOX for testing
"""

import mailbox
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import sys

def create_sample_mbox():
    """Create a sample MBOX file for testing"""
    mbox_path = "sample_emails.mbox"
    
    # Create a new mbox
    mbox = mailbox.mbox(mbox_path)
    
    # Sample email 1: To Australian government
    msg1 = MIMEMultipart()
    msg1['From'] = 'your.name@allfed.info'
    msg1['To'] = 'john.smith@treasury.gov.au, jane.doe@finance.gov.au'
    msg1['Subject'] = 'Food Security Research Collaboration'
    msg1['Date'] = 'Mon, 01 Jan 2024 10:00:00 +0000'
    
    body1 = """Dear John and Jane,

I hope this email finds you well. I'm writing to follow up on our discussion about potential collaboration on food security research.

ALLFED is interested in working with your departments on resilience planning for global food systems. We have some preliminary research that might be of interest.

Would you be available for a call next week to discuss this further?

Best regards,
Your Name
Senior Researcher
Alliance to Feed the Earth in Disasters (ALLFED)
your.name@allfed.info
"""
    msg1.attach(MIMEText(body1, 'plain'))
    mbox.add(msg1)
    
    # Sample email 2: To university
    msg2 = MIMEMultipart()
    msg2['From'] = 'your.name@allfed.info'
    msg2['To'] = 'prof.wilson@anu.edu.au'
    msg2['Subject'] = 'Research Partnership Proposal'
    msg2['Date'] = 'Wed, 15 Feb 2024 14:30:00 +0000'
    
    body2 = """Dear Professor Wilson,

Thank you for your time yesterday discussing our mutual research interests in catastrophic risk assessment.

As discussed, ALLFED would like to propose a formal research partnership with ANU. We believe our expertise in alternative food systems would complement your work on resilience modeling.

I've attached our preliminary proposal for your review.

Looking forward to your feedback.

Best,
Your Name
"""
    msg2.attach(MIMEText(body2, 'plain'))
    mbox.add(msg2)
    
    # Sample email 3: To CSIRO
    msg3 = MIMEMultipart()
    msg3['From'] = 'your.name@allfed.info'
    msg3['To'] = 'researcher@csiro.au'
    msg3['CC'] = 'admin@csiro.au'
    msg3['Subject'] = 'Alternative Protein Research Data Request'
    msg3['Date'] = 'Fri, 20 Mar 2024 09:15:00 +0000'
    
    body3 = """Hello,

I'm reaching out regarding the alternative protein dataset we discussed. ALLFED's analysis of emergency food production systems could greatly benefit from access to this data.

Could we schedule a meeting to discuss data sharing agreements?

Regards,
Your Name
ALLFED Research Team
"""
    msg3.attach(MIMEText(body3, 'plain'))
    mbox.add(msg3)
    
    # Sample email 4: Non-government contact (should be filtered)
    msg4 = MIMEMultipart()
    msg4['From'] = 'your.name@allfed.info'
    msg4['To'] = 'contact@some-company.com'
    msg4['Subject'] = 'General inquiry'
    msg4['Date'] = 'Mon, 10 Apr 2024 16:00:00 +0000'
    
    body4 = "This is a general business inquiry."
    msg4.attach(MIMEText(body4, 'plain'))
    mbox.add(msg4)
    
    mbox.close()
    print(f"Created sample MBOX file: {mbox_path}")
    print(f"Contains {len(mbox)} sample emails")
    
    return mbox_path

def test_extraction():
    """Test the email extraction system"""
    print("Creating sample MBOX file...")
    mbox_path = create_sample_mbox()
    
    print("\nTesting email extraction...")
    
    # Import and run the extractor
    try:
        from email_contact_extractor import EmailContactExtractor
        
        # Create test output directory
        output_dir = "test_output"
        Path(output_dir).mkdir(exist_ok=True)
        
        # Run extraction
        extractor = EmailContactExtractor(mbox_path, output_dir)
        extractor.process_mbox()
        extractor.export_contacts()
        extractor.generate_report()
        
        print(f"\nTest completed successfully!")
        print(f"Check the '{output_dir}' directory for results.")
        
        # Clean up
        Path(mbox_path).unlink(missing_ok=True)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_extraction():
        print("\nEmail extraction system is working correctly!")
        print("You can now process your real MBOX file using:")
        print("python email_contact_extractor.py --mbox your_takeout.mbox")
    else:
        print("Test failed. Please check the error messages above.")
        sys.exit(1) 