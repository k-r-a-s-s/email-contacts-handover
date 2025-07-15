#!/usr/bin/env python3
"""
Create a comprehensive summary CSV for LLM processing
Includes contact details and recent email context for relationship analysis
"""

import pandas as pd
import json
from pathlib import Path
import click
from datetime import datetime
import re

def clean_subject(subject):
    """Clean email subject for better readability"""
    if not subject:
        return ""
    
    # Remove common email artifacts
    subject = re.sub(r'=\?UTF-8\?Q\?.*?\?=', '', subject)
    subject = re.sub(r'\r\n\s*', ' ', subject)
    subject = re.sub(r'\s+', ' ', subject)
    
    # Remove common prefixes
    prefixes = ['Re: ', 'RE: ', 'Fwd: ', 'FWD: ', 'Limited Availability Re: ', 'Parental Leave Re: ']
    for prefix in prefixes:
        if subject.startswith(prefix):
            subject = subject[len(prefix):]
            break
    
    return subject.strip()

def extract_recent_context(interactions_data, email, max_interactions=5):
    """Extract recent interaction context for an email"""
    if email not in interactions_data:
        return {
            'recent_subjects': '',
            'interaction_summary': 'No detailed interactions found',
            'relationship_indicators': '',
            'best_email_sample': ''
        }
    
    interactions = interactions_data[email]
    
    # Sort by date (most recent first) if we have dates
    try:
        interactions_sorted = sorted(interactions, 
                                   key=lambda x: datetime.strptime(x['date'], '%a, %d %b %Y %H:%M:%S %z'), 
                                   reverse=True)
    except:
        # Fall back to original order if date parsing fails
        interactions_sorted = interactions
    
    # Get recent subjects
    recent_subjects = []
    for interaction in interactions_sorted[:max_interactions]:
        subject = clean_subject(interaction.get('subject', ''))
        if subject and subject not in recent_subjects:
            recent_subjects.append(subject)
    
    # Create interaction summary
    total_interactions = len(interactions)
    date_range = ""
    if interactions_sorted:
        try:
            latest_date = interactions_sorted[0].get('date', '')
            oldest_date = interactions_sorted[-1].get('date', '')
            if latest_date and oldest_date:
                date_range = f"({latest_date.split()[0]} to {oldest_date.split()[0]})"
        except:
            pass
    
    interaction_summary = f"{total_interactions} interactions {date_range}".strip()
    
    # Identify relationship indicators
    all_subjects = [clean_subject(i.get('subject', '')) for i in interactions]
    relationship_indicators = []
    
    # Look for meeting/collaboration indicators
    meeting_keywords = ['meeting', 'call', 'discussion', 'invitation', 'catch up', 'follow up']
    collaboration_keywords = ['collaboration', 'project', 'partnership', 'proposal', 'application']
    formal_keywords = ['[SEC=OFFICIAL]', 'official', 'clearance', 'submission']
    funding_keywords = ['fund', 'grant', 'budget', 'funding', 'drf', 'disaster ready fund']
    
    if any(keyword in ' '.join(all_subjects).lower() for keyword in meeting_keywords):
        relationship_indicators.append('Meetings/Calls')
    if any(keyword in ' '.join(all_subjects).lower() for keyword in collaboration_keywords):
        relationship_indicators.append('Active Collaboration')
    if any(keyword in ' '.join(all_subjects).lower() for keyword in formal_keywords):
        relationship_indicators.append('Formal Government')
    if any(keyword in ' '.join(all_subjects).lower() for keyword in funding_keywords):
        relationship_indicators.append('Funding Related')
    
    # Check interaction frequency for relationship strength
    if total_interactions >= 20:
        relationship_indicators.append('High Engagement')
    elif total_interactions >= 10:
        relationship_indicators.append('Regular Contact')
    elif total_interactions >= 5:
        relationship_indicators.append('Moderate Contact')
    
    # Combine multiple email snippets for rich context
    email_snippets = []
    
    for interaction in interactions_sorted[:5]:  # Take top 5 recent interactions
        snippet = interaction.get('body_snippet', '')
        if snippet and len(snippet.strip()) > 50:  # Must be substantial
            # Clean up the snippet
            clean_snippet = snippet.replace('\r\n', '\n').replace('\r', '\n')
            clean_snippet = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_snippet)
            clean_snippet = clean_snippet.strip()
            
            # Add context about when this was sent
            subject = clean_subject(interaction.get('subject', ''))
            date = interaction.get('date', '')
            date_part = date.split(',')[1].strip() if ',' in date else date
            
            snippet_with_context = f"[{date_part} - {subject}]\n{clean_snippet}"
            email_snippets.append(snippet_with_context)
    
    # Combine snippets with separators
    best_email_sample = "\n\n---\n\n".join(email_snippets)
    
    # Cap at reasonable length for LLM processing
    if len(best_email_sample) > 2500:
        best_email_sample = best_email_sample[:2500] + "..."
    
    return {
        'recent_subjects': ' | '.join(recent_subjects[:5]),
        'interaction_summary': interaction_summary,
        'relationship_indicators': ', '.join(relationship_indicators),
        'best_email_sample': best_email_sample
    }

def categorize_organization(domain, organization, email):
    """Categorize the type of organization"""
    domain_lower = domain.lower()
    org_lower = organization.lower() if organization else ""
    email_lower = email.lower()
    
    # Government categories
    if any(pattern in domain_lower for pattern in ['.gov.au', '.qld.gov.au', '.nsw.gov.au', '.vic.gov.au', '.sa.gov.au', '.wa.gov.au', '.tas.gov.au', '.act.gov.au', '.nt.gov.au']):
        return 'Australian Government'
    elif '.edu.au' in domain_lower:
        return 'Australian University'
    elif '.org.au' in domain_lower:
        return 'Australian Organization'
    elif '.com.au' in domain_lower:
        return 'Australian Business'
    
    # International government/academic
    elif any(pattern in domain_lower for pattern in ['.gov', '.edu']):
        return 'International Gov/Academic'
    
    # NGOs and foundations
    elif any(pattern in org_lower for pattern in ['foundation', 'charity', 'ngo', 'nonprofit']):
        return 'NGO/Foundation'
    
    # Research and think tanks
    elif any(pattern in org_lower for pattern in ['research', 'institute', 'think tank', 'university']):
        return 'Research/Think Tank'
    
    # Business/Corporate
    elif any(pattern in domain_lower for pattern in ['.com', '.org', '.net']):
        if 'gmail.com' in domain_lower or 'hotmail.com' in domain_lower or 'outlook.com' in domain_lower:
            return 'Individual/Personal'
        else:
            return 'Business/Corporate'
    
    return 'Other'

def create_llm_summary(contacts_file, interactions_file, output_file):
    """Create comprehensive summary for LLM processing"""
    
    print("Loading contacts and interactions...")
    
    # Load contacts
    contacts_df = pd.read_csv(contacts_file)
    print(f"Loaded {len(contacts_df)} contacts")
    
    # Load interactions
    with open(interactions_file, 'r') as f:
        interactions_data = json.load(f)
    print(f"Loaded interaction data for {len(interactions_data)} contacts")
    
    # Create enhanced summary
    summary_data = []
    
    for _, contact in contacts_df.iterrows():
        email = contact['email']
        
        # Extract context from interactions
        context = extract_recent_context(interactions_data, email)
        
        # Categorize organization
        org_category = categorize_organization(
            contact.get('domain', ''), 
            contact.get('organization', ''), 
            email
        )
        
        # Calculate engagement score (simple metric)
        interaction_count = contact.get('interaction_count', 0)
        if interaction_count >= 50:
            engagement_level = 'Very High'
        elif interaction_count >= 20:
            engagement_level = 'High'
        elif interaction_count >= 10:
            engagement_level = 'Medium'
        elif interaction_count >= 5:
            engagement_level = 'Low'
        else:
            engagement_level = 'Minimal'
        
        # Handle NaN values properly
        name = contact.get('name', '')
        if pd.isna(name) or not name:
            contact_name = email.split('@')[0]
        else:
            contact_name = str(name).replace(',', '')
        
        organization = contact.get('organization', '')
        if pd.isna(organization):
            organization = ''
        else:
            organization = str(organization).replace(',', '')
        
        summary_data.append({
            'contact_name': contact_name,
            'email': email,
            'domain': contact.get('domain', ''),
            'organization': organization,
            'organization_category': org_category,
            'is_australian_government': contact.get('is_australian_government', False),
            'interaction_count': interaction_count,
            'engagement_level': engagement_level,
            'first_contact': str(contact.get('first_contact', '')) if pd.notna(contact.get('first_contact')) else '',
            'last_contact': str(contact.get('last_contact', '')) if pd.notna(contact.get('last_contact')) else '',
            'interaction_summary': context['interaction_summary'],
            'recent_email_subjects': context['recent_subjects'],
            'relationship_indicators': context['relationship_indicators'],
            'sample_email_context': context['best_email_sample'] if context['best_email_sample'] else (str(contact.get('email_sample', '')) if pd.notna(contact.get('email_sample')) and contact.get('email_sample') else '')
        })
    
    # Create DataFrame and sort by engagement level and interaction count
    summary_df = pd.DataFrame(summary_data)
    
    # Custom sort order for engagement levels
    engagement_order = {'Very High': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Minimal': 1}
    summary_df['engagement_sort'] = summary_df['engagement_level'].map(engagement_order)
    summary_df = summary_df.sort_values(['is_australian_government', 'engagement_sort', 'interaction_count'], 
                                       ascending=[False, False, False])
    summary_df = summary_df.drop('engagement_sort', axis=1)
    
    # Save to CSV
    summary_df.to_csv(output_file, index=False)
    
    # Print summary statistics
    print(f"\n{'='*70}")
    print("LLM-READY CONTACT SUMMARY CREATED")
    print(f"{'='*70}")
    print(f"Total contacts: {len(summary_df)}")
    print(f"Australian government contacts: {len(summary_df[summary_df['is_australian_government'] == True])}")
    
    print(f"\nBy organization category:")
    category_counts = summary_df['organization_category'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count}")
    
    print(f"\nBy engagement level:")
    engagement_counts = summary_df['engagement_level'].value_counts()
    for level in ['Very High', 'High', 'Medium', 'Low', 'Minimal']:
        if level in engagement_counts:
            print(f"  {level}: {engagement_counts[level]}")
    
    print(f"\nTop 10 most engaged contacts:")
    top_contacts = summary_df.head(10)[['contact_name', 'organization', 'interaction_count', 'engagement_level']]
    for _, contact in top_contacts.iterrows():
        print(f"  {contact['contact_name']} ({contact['organization']}) - {contact['interaction_count']} interactions ({contact['engagement_level']})")
    
    print(f"\nSummary saved to: {output_file}")
    print("Ready for LLM processing!")

@click.command()
@click.option('--contacts-file', default='output/contacts_all_cleaned.csv', help='Cleaned contacts CSV file')
@click.option('--interactions-file', default='output/contact_interactions.json', help='Interactions JSON file')
@click.option('--output-file', default='output/contacts_llm_summary.csv', help='Output summary CSV for LLM processing')
def main(contacts_file, interactions_file, output_file):
    """Create comprehensive contact summary optimized for LLM relationship analysis"""
    
    # Check if files exist
    if not Path(contacts_file).exists():
        click.echo(f"Error: Contacts file not found: {contacts_file}")
        return
    
    if not Path(interactions_file).exists():
        click.echo(f"Error: Interactions file not found: {interactions_file}")
        return
    
    # Create summary
    create_llm_summary(contacts_file, interactions_file, output_file)

if __name__ == "__main__":
    main() 