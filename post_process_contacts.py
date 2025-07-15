#!/usr/bin/env python3
"""
Post-processing script for cleaning extracted contacts
Removes:
1. Internal ALLFED collaborators (emails with "Research Strategy Session" subject)
2. Gmail bounce domains (docos.bounces.google.com)
"""

import pandas as pd
import json
from pathlib import Path
import click
from typing import Set

def load_interaction_data(interactions_file: str) -> dict:
    """Load interaction data from JSON file"""
    print("Loading interaction data...")
    with open(interactions_file, 'r') as f:
        interactions = json.load(f)
    return interactions

def find_research_strategy_contacts(interactions: dict) -> Set[str]:
    """Find contacts who have emails with 'Research Strategy Session' in subject"""
    research_strategy_contacts = set()
    
    print("Scanning for 'Research Strategy Session' subjects...")
    for email, interaction_list in interactions.items():
        for interaction in interaction_list:
            subject = interaction.get('subject', '').lower()
            if 'research strategy session' in subject:
                research_strategy_contacts.add(email)
                print(f"  Found internal collaborator: {email}")
                break  # No need to check more interactions for this contact
    
    print(f"Found {len(research_strategy_contacts)} contacts with 'Research Strategy Session' subjects")
    return research_strategy_contacts

def clean_contacts(input_file: str, output_file: str, interactions_file: str) -> None:
    """Clean the contacts CSV by removing unwanted contacts"""
    
    # Load contacts
    print(f"Loading contacts from {input_file}...")
    df = pd.read_csv(input_file)
    initial_count = len(df)
    print(f"Initial contact count: {initial_count}")
    
    # Load interactions to find Research Strategy Session contacts
    interactions = load_interaction_data(interactions_file)
    research_strategy_contacts = find_research_strategy_contacts(interactions)
    
    # Filter out Research Strategy Session contacts
    print("\nFiltering out Research Strategy Session contacts...")
    before_research_filter = len(df)
    df = df[~df['email'].isin(research_strategy_contacts)]
    after_research_filter = len(df)
    research_removed = before_research_filter - after_research_filter
    print(f"Removed {research_removed} Research Strategy Session contacts")
    
    # Filter out docos.bounces.google.com domain
    print("\nFiltering out docos.bounces.google.com domain...")
    before_bounce_filter = len(df)
    df = df[df['domain'] != 'docos.bounces.google.com']
    after_bounce_filter = len(df)
    bounce_removed = before_bounce_filter - after_bounce_filter
    print(f"Removed {bounce_removed} docos.bounces.google.com contacts")
    
    # Additional cleanup - remove other common bounce domains
    bounce_domains = [
        'bounce.researchgatemail.net',
        'doclist.bounces.google.com',
        'bot.trellobutler.com'
    ]
    
    print(f"\nFiltering out additional bounce domains: {bounce_domains}")
    before_additional_filter = len(df)
    df = df[~df['domain'].isin(bounce_domains)]
    after_additional_filter = len(df)
    additional_removed = before_additional_filter - after_additional_filter
    print(f"Removed {additional_removed} additional bounce domain contacts")
    
    # Save cleaned contacts
    df.to_csv(output_file, index=False)
    
    # Print summary
    final_count = len(df)
    total_removed = initial_count - final_count
    
    print(f"\n{'='*60}")
    print("CONTACT CLEANING SUMMARY")
    print(f"{'='*60}")
    print(f"Initial contacts: {initial_count:,}")
    print(f"Research Strategy Session removed: {research_removed:,}")
    print(f"docos.bounces.google.com removed: {bounce_removed:,}")
    print(f"Additional bounce domains removed: {additional_removed:,}")
    print(f"Total removed: {total_removed:,}")
    print(f"Final contacts: {final_count:,}")
    print(f"Percentage retained: {(final_count/initial_count)*100:.1f}%")
    print(f"\nCleaned contacts saved to: {output_file}")
    
    # Show breakdown by Australian government status
    if 'is_australian_government' in df.columns:
        au_gov_count = len(df[df['is_australian_government'] == True])
        print(f"Australian government contacts retained: {au_gov_count:,}")
    
    # Show top domains after cleaning
    print(f"\nTop 10 domains after cleaning:")
    domain_counts = df['domain'].value_counts().head(10)
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
    """Clean contacts by removing internal collaborators and bounce domains"""
    
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
    
    click.echo(f"\nPost-processing complete!")
    click.echo(f"Main cleaned file: {output_file}")
    click.echo(f"Australian gov file: {Path(output_dir) / 'contacts_australian_government_cleaned.csv'}")

if __name__ == "__main__":
    main() 