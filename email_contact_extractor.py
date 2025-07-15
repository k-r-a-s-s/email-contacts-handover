#!/usr/bin/env python3
"""
Email Contact Extractor for ALLFED Handover
Extracts government contacts from Google Takeout MBOX files
"""

import os
import re
import json
import mailbox
import email
from email.utils import parseaddr, getaddresses
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Optional, Tuple
import pandas as pd
from pathlib import Path
import click
from tqdm import tqdm
import csv
from email_validator import validate_email, EmailNotValidError


class EmailContactExtractor:
    def __init__(self, mbox_path: str, output_dir: str = "output"):
        self.mbox_path = mbox_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Australian government/org domains
        self.au_gov_domains = {
            '.gov.au', '.org.au', '.edu.au', '.asn.au', '.id.au'
        }
        
        # Known ALLFED domains to exclude
        self.internal_domains = {
            'allfed.info', 'allfed.org', 'allfed.net'
        }
        
        # Contact storage
        self.contacts = {}
        self.email_threads = defaultdict(list)
        
    def is_australian_government_domain(self, email_addr: str) -> bool:
        """Check if email domain is Australian government/org"""
        domain = email_addr.split('@')[-1].lower()
        return any(domain.endswith(suffix) for suffix in self.au_gov_domains)
    
    def is_internal_email(self, email_addr: str) -> bool:
        """Check if email is internal ALLFED email"""
        domain = email_addr.split('@')[-1].lower()
        return any(domain.endswith(suffix) for suffix in self.internal_domains)
    
    def extract_email_info(self, msg) -> Dict:
        """Extract relevant information from email message"""
        info = {
            'subject': msg.get('Subject', ''),
            'date': msg.get('Date', ''),
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'cc': msg.get('CC', ''),
            'bcc': msg.get('BCC', ''),
            'message_id': msg.get('Message-ID', ''),
            'in_reply_to': msg.get('In-Reply-To', ''),
            'references': msg.get('References', ''),
            'body': self.extract_body(msg)
        }
        return info
    
    def extract_body(self, msg) -> str:
        """Extract email body text"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())
        return body[:5000]  # Limit body length
    
    def parse_email_addresses(self, addr_string: str) -> List[Tuple[str, str]]:
        """Parse email addresses from header string"""
        if not addr_string:
            return []
        
        try:
            addresses = getaddresses([addr_string])
            validated_addresses = []
            
            for name, email_addr in addresses:
                if email_addr:
                    try:
                        # Basic validation
                        validate_email(email_addr)
                        validated_addresses.append((name.strip(), email_addr.strip().lower()))
                    except EmailNotValidError:
                        continue
            
            return validated_addresses
        except Exception as e:
            print(f"Error parsing addresses '{addr_string}': {e}")
            return []
    
    def extract_organization_from_signature(self, body: str) -> Optional[str]:
        """Extract organization name from email signature"""
        # Common signature patterns
        patterns = [
            r'(?:^|\n)([^,\n]+),?\s*\n[^@\n]*@[^@\n]+\.(?:gov|org|edu)\.au',
            r'(?:^|\n)([A-Z][^,\n]{10,50})\s*\n.*?(?:gov|org|edu)\.au',
            r'(?:Department of|Ministry of|Office of|Agency for)\s+([A-Z][^,\n]{5,40})',
            r'(?:^|\n)([A-Z][^,\n]{5,40})\s*(?:Department|Ministry|Office|Agency|Commission)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, body, re.MULTILINE | re.IGNORECASE)
            if matches:
                org = matches[0].strip()
                if len(org) > 5 and not '@' in org:
                    return org
        
        return None
    
    def process_mbox(self) -> None:
        """Process the MBOX file and extract contacts"""
        print(f"Processing MBOX file: {self.mbox_path}")
        
        try:
            mbox = mailbox.mbox(self.mbox_path)
            total_messages = len(mbox)
            print(f"Found {total_messages} messages")
            
            sent_emails = []
            
            with tqdm(total=total_messages, desc="Processing emails") as pbar:
                for message in mbox:
                    pbar.update(1)
                    
                    # Extract email info
                    email_info = self.extract_email_info(message)
                    
                    # Check if this is a sent email (usually in Sent folder or has specific headers)
                    from_addr = email_info['from']
                    
                    # Skip if no from address
                    if not from_addr:
                        continue
                    
                    # Parse from address
                    from_addresses = self.parse_email_addresses(from_addr)
                    if not from_addresses:
                        continue
                    
                    from_name, from_email = from_addresses[0]
                    
                    # Check if this is likely a sent email (from ALLFED domain)
                    if not self.is_internal_email(from_email):
                        continue
                    
                    # Extract recipients
                    recipients = []
                    for header in ['to', 'cc', 'bcc']:
                        if email_info[header]:
                            recipients.extend(self.parse_email_addresses(email_info[header]))
                    
                    # Filter for external recipients
                    external_recipients = [
                        (name, email_addr) for name, email_addr in recipients
                        if not self.is_internal_email(email_addr)
                    ]
                    
                    if external_recipients:
                        sent_emails.append({
                            'email_info': email_info,
                            'recipients': external_recipients,
                            'from_name': from_name,
                            'from_email': from_email
                        })
            
            print(f"Found {len(sent_emails)} sent emails with external recipients")
            self.process_sent_emails(sent_emails)
            
        except Exception as e:
            print(f"Error processing MBOX: {e}")
            raise
    
    def process_sent_emails(self, sent_emails: List[Dict]) -> None:
        """Process sent emails to extract contacts"""
        contact_interactions = defaultdict(list)
        
        for email_data in tqdm(sent_emails, desc="Extracting contacts"):
            email_info = email_data['email_info']
            recipients = email_data['recipients']
            
            # Extract organization from email body
            org_from_signature = self.extract_organization_from_signature(email_info['body'])
            
            for name, email_addr in recipients:
                # Skip if already internal
                if self.is_internal_email(email_addr):
                    continue
                
                # Extract domain info
                domain = email_addr.split('@')[-1]
                is_au_gov = self.is_australian_government_domain(email_addr)
                
                # Create contact entry
                contact_key = email_addr
                
                if contact_key not in self.contacts:
                    self.contacts[contact_key] = {
                        'name': name or '',
                        'email': email_addr,
                        'domain': domain,
                        'is_australian_government': is_au_gov,
                        'organization': org_from_signature or self.guess_organization_from_domain(domain),
                        'first_contact': email_info['date'],
                        'last_contact': email_info['date'],
                        'interaction_count': 0,
                        'subjects': [],
                        'email_sample': email_info['body'][:2000]
                    }
                
                # Update contact info
                contact = self.contacts[contact_key]
                contact['interaction_count'] += 1
                contact['last_contact'] = email_info['date']
                contact['subjects'].append(email_info['subject'])
                
                # Update name if we have a better one
                if name and (not contact['name'] or len(name) > len(contact['name'])):
                    contact['name'] = name
                
                # Update organization if we found one
                if org_from_signature and not contact['organization']:
                    contact['organization'] = org_from_signature
                
                # Store interaction
                contact_interactions[contact_key].append({
                    'date': email_info['date'],
                    'subject': email_info['subject'],
                    'body_snippet': email_info['body'][:300]
                })
        
        # Save interaction details
        self.save_interaction_details(contact_interactions)
        
        print(f"Extracted {len(self.contacts)} unique contacts")
        au_gov_contacts = [c for c in self.contacts.values() if c['is_australian_government']]
        print(f"Found {len(au_gov_contacts)} Australian government contacts")
    
    def guess_organization_from_domain(self, domain: str) -> str:
        """Guess organization name from domain"""
        # Remove common suffixes
        domain_clean = domain.replace('.gov.au', '').replace('.org.au', '').replace('.edu.au', '')
        
        # Common government department mappings
        dept_mappings = {
            'treasury': 'Department of Treasury',
            'finance': 'Department of Finance',
            'agriculture': 'Department of Agriculture',
            'industry': 'Department of Industry',
            'health': 'Department of Health',
            'education': 'Department of Education',
            'environment': 'Department of Environment',
            'defence': 'Department of Defence',
            'dfat': 'Department of Foreign Affairs and Trade',
            'austrade': 'Australian Trade and Investment Commission',
            'csiro': 'Commonwealth Scientific and Industrial Research Organisation',
            'abs': 'Australian Bureau of Statistics',
            'rba': 'Reserve Bank of Australia',
            'accc': 'Australian Competition and Consumer Commission',
        }
        
        domain_key = domain_clean.split('.')[0].lower()
        return dept_mappings.get(domain_key, domain_clean.title())
    
    def save_interaction_details(self, interactions: Dict) -> None:
        """Save detailed interaction data"""
        interactions_file = self.output_dir / "contact_interactions.json"
        
        # Convert to serializable format
        serializable_interactions = {}
        for email, interaction_list in interactions.items():
            serializable_interactions[email] = interaction_list
        
        with open(interactions_file, 'w') as f:
            json.dump(serializable_interactions, f, indent=2, default=str)
        
        print(f"Saved interaction details to {interactions_file}")
    
    def export_contacts(self) -> None:
        """Export contacts to various formats"""
        # Convert to DataFrame
        df = pd.DataFrame(list(self.contacts.values()))
        
        if df.empty:
            print("No contacts to export")
            return
        
        # Sort by interaction count and Australian government status
        df = df.sort_values(['is_australian_government', 'interaction_count'], ascending=[False, False])
        
        # Export to CSV
        csv_file = self.output_dir / "contacts_all.csv"
        df.to_csv(csv_file, index=False)
        print(f"Exported all contacts to {csv_file}")
        
        # Export Australian government contacts only
        au_gov_df = df[df['is_australian_government'] == True]
        if not au_gov_df.empty:
            au_gov_file = self.output_dir / "contacts_australian_government.csv"
            au_gov_df.to_csv(au_gov_file, index=False)
            print(f"Exported {len(au_gov_df)} Australian government contacts to {au_gov_file}")
        
        # Export to Excel with multiple sheets
        excel_file = self.output_dir / "contacts_summary.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Contacts', index=False)
            if not au_gov_df.empty:
                au_gov_df.to_excel(writer, sheet_name='AU Government', index=False)
            
            # Summary statistics
            summary_df = pd.DataFrame({
                'Category': ['Total Contacts', 'Australian Government', 'High Interaction (5+)', 'Recent (2023+)'],
                'Count': [
                    len(df),
                    len(au_gov_df),
                    len(df[df['interaction_count'] >= 5]),
                    len(df[df['last_contact'].str.contains('2023|2024', na=False)])
                ]
            })
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"Exported Excel summary to {excel_file}")
    
    def generate_report(self) -> None:
        """Generate a summary report"""
        report_file = self.output_dir / "contact_extraction_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("ALLFED Email Contact Extraction Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"MBOX File: {self.mbox_path}\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total unique contacts: {len(self.contacts)}\n")
            
            au_gov_contacts = [c for c in self.contacts.values() if c['is_australian_government']]
            f.write(f"Australian government contacts: {len(au_gov_contacts)}\n")
            
            high_interaction = [c for c in self.contacts.values() if c['interaction_count'] >= 5]
            f.write(f"High interaction contacts (5+ emails): {len(high_interaction)}\n\n")
            
            # Top domains
            f.write("TOP DOMAINS\n")
            f.write("-" * 12 + "\n")
            domain_counts = Counter(c['domain'] for c in self.contacts.values())
            for domain, count in domain_counts.most_common(10):
                f.write(f"{domain}: {count}\n")
            f.write("\n")
            
            # Top Australian government contacts
            if au_gov_contacts:
                f.write("TOP AUSTRALIAN GOVERNMENT CONTACTS\n")
                f.write("-" * 35 + "\n")
                au_gov_sorted = sorted(au_gov_contacts, key=lambda x: x['interaction_count'], reverse=True)
                for contact in au_gov_sorted[:10]:
                    f.write(f"{contact['name']} <{contact['email']}> - {contact['interaction_count']} interactions\n")
                    f.write(f"  Organization: {contact['organization']}\n")
                    f.write(f"  Last contact: {contact['last_contact']}\n\n")
        
        print(f"Generated report: {report_file}")


@click.command()
@click.option('--mbox', required=True, help='Path to MBOX file')
@click.option('--output', default='output', help='Output directory')
@click.option('--llm-enhance', is_flag=True, help='Use LLM to enhance contact descriptions (requires API keys)')
def main(mbox: str, output: str, llm_enhance: bool):
    """Extract government contacts from MBOX file"""
    
    if not os.path.exists(mbox):
        click.echo(f"Error: MBOX file not found: {mbox}")
        return
    
    # Initialize extractor
    extractor = EmailContactExtractor(mbox, output)
    
    # Process MBOX
    extractor.process_mbox()
    
    # Export results
    extractor.export_contacts()
    
    # Generate report
    extractor.generate_report()
    
    if llm_enhance:
        click.echo("LLM enhancement feature coming soon...")
        # Future: Add LLM enhancement functionality
    
    click.echo(f"\nExtraction complete! Check the '{output}' directory for results.")


if __name__ == "__main__":
    main() 