#!/usr/bin/env python3
"""
Enhanced post-processing script for cleaning extracted contacts
Removes:
1. Internal ALLFED team members (emails with various internal subjects)
2. Bounce/automated emails by checking email address patterns
"""

import pandas as pd
import json
from pathlib import Path
import click
from typing import Set
import re

def load_interaction_data(interactions_file: str) -> dict:
    """Load interaction data from JSON file"""
    print("Loading interaction data...")
    with open(interactions_file, 'r') as f:
        interactions = json.load(f)
    return interactions

def find_internal_collaborator_contacts(interactions: dict) -> Set[str]:
    """Find contacts who have emails with internal ALLFED team subjects"""
    internal_contacts = set()
    
    # Internal subject patterns to filter out
    internal_subjects = [
        'research strategy session',
        'inclusion & diversity survey 2023',
        'allfed london team day', 
        'transgender fireside chat',
        'allfed okrs',
        'kpis exchange',
        "farrah's birthday"
    ]
    
    print("Scanning for internal ALLFED team subjects...")
    for email, interaction_list in interactions.items():
        for interaction in interaction_list:
            subject = interaction.get('subject', '').lower()
            for internal_pattern in internal_subjects:
                if internal_pattern in subject:
                    internal_contacts.add(email)
                    print(f"  Found internal collaborator: {email} (subject: {internal_pattern})")
                    break  # No need to check more patterns for this interaction
            if email in internal_contacts:
                break  # No need to check more interactions for this contact
    
    print(f"Found {len(internal_contacts)} contacts with internal ALLFED team subjects")
    return internal_contacts

def is_bounce_or_automated_email(email: str) -> bool:
    """Check if email address indicates it's a bounce or automated email"""
    email_lower = email.lower()
    
    # Patterns that indicate bounce/automated emails
    bounce_patterns = [
        'bounces',           # Generic bounce patterns
        'noreply',           # No-reply addresses
        'no-reply',          # Alternative no-reply format
        'notifications',     # Notification emails
        'mailer-daemon',     # Mail system responses
        'postmaster',        # Mail admin
        'do-not-reply',      # Alternative format
        'donotreply',        # Alternative format
        'auto-reply',        # Auto-response
        'autoreply',         # Auto-response
        'system@',           # System emails
        'automated@',        # Automated systems
        'alert@',            # Alert systems
        'digest@',           # Digest emails
        'newsletter@',       # Newsletters (automated)
        'updates@',          # Update notifications
        'tickets@',          # Ticket systems
        'marketing@',        # Marketing automation
        'promo@',            # Promotional emails
        'campaigns@',        # Campaign emails
        'surveys@',          # Survey systems
        'feedback@',         # Feedback systems
        'reports@',          # Report generation
        'alerts@',           # Alert systems
        'service@',          # Service notifications
        'account-security-noreply@',  # Microsoft patterns
        'allfedprojects-noreply@',    # Trello patterns
    ]
    
    # Special patterns for complex bounce emails
    complex_patterns = [
        r'bounces\+.*@',           # bounces+numbers@domain
        r'msprvs\d+=.*bounces',    # Microsoft bounce patterns
        r'\d{8}-\w{4}-\w{4}@.*bounces',  # ID-based bounces
        r'[a-z0-9]{20,}@.*bounces',      # Long random strings
        r'[a-z0-9\-]{30,}@chime-notifications',  # Google chime patterns
        r'[a-z0-9\-]{30,}@.*\.bounces\.',        # Generic long bounce patterns
        r'[a-z0-9]{30,}@bounce\.researchgatemail\.net',  # ResearchGate bounces
        r'prvs=.*@',               # Microsoft prvs patterns
    ]
    
    # Check simple patterns
    for pattern in bounce_patterns:
        if pattern in email_lower:
            return True
    
    # Check complex regex patterns
    for pattern in complex_patterns:
        if re.search(pattern, email_lower):
            return True
    
    # Check for domains that are primarily bounce/notification services
    bounce_domains = [
        '.bounces.google.com',
        '.bounces.',
        'em9672.mail.anthropic.com',  # Anthropic marketing
        'em3917.conlog.com.au',       # Conference marketing
        'sendfox.longgameproject.org', # Marketing automation
        'bounces.gov1.qemailserver.com',
        'accountprotection.microsoft.com',
        'groupgreeting.com',
        'trellobutler.com',
    ]
    
    for domain_pattern in bounce_domains:
        if domain_pattern in email_lower:
            return True
    
    return False

def clean_contacts(input_file: str, output_file: str, interactions_file: str) -> None:
    """Clean the contacts CSV by removing unwanted contacts"""
    
    # Load contacts
    print(f"Loading contacts from {input_file}...")
    df = pd.read_csv(input_file)
    initial_count = len(df)
    print(f"Initial contact count: {initial_count}")
    
    # Load interactions to find internal ALLFED team contacts
    interactions = load_interaction_data(interactions_file)
    internal_contacts = find_internal_collaborator_contacts(interactions)
    
    # Filter out internal ALLFED team contacts
    print("\nFiltering out internal ALLFED team contacts...")
    before_internal_filter = len(df)
    df = df[~df['email'].isin(internal_contacts)]
    after_internal_filter = len(df)
    internal_removed = before_internal_filter - after_internal_filter
    print(f"Removed {internal_removed} internal ALLFED team contacts")
    
    # Filter out bounce/automated emails
    print("\nFiltering out bounce and automated email addresses...")
    before_bounce_filter = len(df)
    
    # Create a mask for bounce emails
    bounce_mask = df['email'].apply(is_bounce_or_automated_email)
    bounce_emails = df[bounce_mask]['email'].tolist()
    
    # Show some examples
    if bounce_emails:
        print(f"Example bounce emails being removed:")
        for email in bounce_emails[:10]:  # Show first 10
            print(f"  {email}")
        if len(bounce_emails) > 10:
            print(f"  ... and {len(bounce_emails) - 10} more")
    
    # Apply the filter
    df = df[~bounce_mask]
    after_bounce_filter = len(df)
    bounce_removed = before_bounce_filter - after_bounce_filter
    print(f"Removed {bounce_removed} bounce/automated email contacts")
    
    # Save cleaned contacts
    df.to_csv(output_file, index=False)
    
    # Print summary
    final_count = len(df)
    total_removed = initial_count - final_count
    
    print(f"\n{'='*70}")
    print("ENHANCED CONTACT CLEANING SUMMARY")
    print(f"{'='*70}")
    print(f"Initial contacts: {initial_count:,}")
    print(f"Internal ALLFED team removed: {internal_removed:,}")
    print(f"Bounce/automated emails removed: {bounce_removed:,}")
    print(f"Total removed: {total_removed:,}")
    print(f"Final contacts: {final_count:,}")
    print(f"Percentage retained: {(final_count/initial_count)*100:.1f}%")
    print(f"\nCleaned contacts saved to: {output_file}")
    
    # Show breakdown by Australian government status
    if 'is_australian_government' in df.columns:
        au_gov_count = len(df[df['is_australian_government'] == True])
        print(f"Australian government contacts retained: {au_gov_count:,}")
    
    # Show top domains after cleaning
    print(f"\nTop 15 domains after enhanced cleaning:")
    domain_counts = df['domain'].value_counts().head(15)
    for domain, count in domain_counts.items():
        print(f"  {domain}: {count}")

def create_cleaned_australian_gov_file(cleaned_contacts_file: str, output_dir: str) -> None:
    """Create a separate file for Australian government contacts from cleaned data"""
    df = pd.read_csv(cleaned_contacts_file)
    
    if 'is_australian_government' in df.columns:
        au_gov_df = df[df['is_australian_government'] == True]
        
        if not au_gov_df.empty:
            # Sort by interaction count
            au_gov_df = au_gov_df.sort_values('interaction_count', ascending=False)
            
            au_gov_file = Path(output_dir) / "contacts_australian_government_cleaned.csv"
            au_gov_df.to_csv(au_gov_file, index=False)
            print(f"Australian government contacts saved to: {au_gov_file}")
            print(f"Australian government contacts count: {len(au_gov_df)}")
        else:
            print("No Australian government contacts found after cleaning")

@click.command()
@click.option('--input-file', default='output/contacts_all.csv', help='Input contacts CSV file')
@click.option('--output-file', default='output/contacts_all_cleaned.csv', help='Output cleaned contacts CSV file')
@click.option('--interactions-file', default='output/contact_interactions.json', help='Interactions JSON file')
@click.option('--output-dir', default='output', help='Output directory')
def main(input_file: str, output_file: str, interactions_file: str, output_dir: str):
    """Enhanced cleaning: removes internal ALLFED team members and all bounce/automated emails"""
    
    # Check if files exist
    if not Path(input_file).exists():
        click.echo(f"Error: Input file not found: {input_file}")
        return
    
    if not Path(interactions_file).exists():
        click.echo(f"Error: Interactions file not found: {interactions_file}")
        return
    
    # Run cleaning
    clean_contacts(input_file, output_file, interactions_file)
    
    # Create Australian government specific file
    create_cleaned_australian_gov_file(output_file, output_dir)
    
    click.echo(f"\nEnhanced post-processing complete!")
    click.echo(f"Main cleaned file: {output_file}")
    click.echo(f"Australian gov file: {Path(output_dir) / 'contacts_australian_government_cleaned.csv'}")

if __name__ == "__main__":
    main() 