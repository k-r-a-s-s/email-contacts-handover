#!/usr/bin/env python3
"""
Create a focused LLM summary CSV for important contacts only
Pulls maximum context (20 emails) for each important contact
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

def extract_domain_from_email(email):
    """Extract domain from email address"""
    return email.split('@')[1] if '@' in email else ''

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

def derive_organization_from_domain(domain):
    """Try to derive organization name from domain"""
    if not domain:
        return ""
    
    # Remove common TLDs and subdomains
    domain_parts = domain.lower().split('.')
    
    # Handle Australian government domains
    if 'gov.au' in domain:
        if len(domain_parts) >= 3:
            return domain_parts[-3].upper()  # e.g., 'sa' from 'sa.gov.au'
        return "Australian Government"
    
    # Handle other domains
    if len(domain_parts) >= 2:
        org_name = domain_parts[-2]
        # Capitalize first letter
        return org_name.capitalize()
    
    return domain

def extract_recent_context(interactions_data, email, max_interactions=20):
    """Extract recent interaction context for an email with maximum context"""
    if email not in interactions_data:
        return {
            'recent_subjects': '',
            'interaction_summary': 'No detailed interactions found',
            'relationship_indicators': '',
            'best_email_sample': '',
            'first_contact': '',
            'last_contact': '',
            'interaction_count': 0,
            'engagement_level': 'None'
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
    for interaction in interactions_sorted[:10]:  # More subjects for important contacts
        subject = clean_subject(interaction.get('subject', ''))
        if subject and subject not in recent_subjects:
            recent_subjects.append(subject)
    
    # Create interaction summary
    total_interactions = len(interactions)
    date_range = ""
    first_contact = ""
    last_contact = ""
    
    if interactions_sorted:
        try:
            latest_date = interactions_sorted[0].get('date', '')
            oldest_date = interactions_sorted[-1].get('date', '')
            last_contact = latest_date
            first_contact = oldest_date
            if latest_date and oldest_date:
                latest_day = latest_date.split()[0] if latest_date else ""
                oldest_day = oldest_date.split()[0] if oldest_date else ""
                date_range = f"({oldest_day}, to {latest_day},)"
        except:
            pass
    
    interaction_summary = f"{total_interactions} interactions {date_range}".strip()
    
    # Determine engagement level
    if total_interactions >= 50:
        engagement_level = "Very High"
    elif total_interactions >= 20:
        engagement_level = "High"
    elif total_interactions >= 10:
        engagement_level = "Medium"
    elif total_interactions >= 5:
        engagement_level = "Low"
    else:
        engagement_level = "Minimal"
    
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
    
    # Combine multiple email snippets for rich context (MAX 20 emails)
    email_snippets = []
    
    for interaction in interactions_sorted[:max_interactions]:  # Take up to max_interactions
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
    
    # Cap at reasonable length for LLM processing (more generous for important contacts)
    if len(best_email_sample) > 5000:
        best_email_sample = best_email_sample[:5000] + "..."
    
    return {
        'recent_subjects': ' | '.join(recent_subjects),
        'interaction_summary': interaction_summary,
        'relationship_indicators': ', '.join(relationship_indicators),
        'best_email_sample': best_email_sample,
        'first_contact': first_contact,
        'last_contact': last_contact,
        'interaction_count': total_interactions,
        'engagement_level': engagement_level
    }

def load_important_contacts(contacts_file):
    """Load important contacts from text file"""
    contacts = []
    with open(contacts_file, 'r') as f:
        for line in f:
            email = line.strip()
            if email and '@' in email:
                contacts.append(email)
    return contacts

def create_important_contacts_summary(important_contacts_file, interactions_file, output_file):
    """Create comprehensive summary for important contacts only with maximum context"""
    
    print("Loading important contacts and interactions...")
    
    # Load important contacts
    important_emails = load_important_contacts(important_contacts_file)
    print(f"Loaded {len(important_emails)} important contacts")
    
    # Load interactions
    with open(interactions_file, 'r') as f:
        interactions_data = json.load(f)
    print(f"Loaded interaction data for {len(interactions_data)} total contacts")
    
    # Create enhanced summary for important contacts only
    summary_data = []
    
    for email in important_emails:
        print(f"Processing {email}...")
        
        # Extract domain and derive basic info
        domain = extract_domain_from_email(email)
        organization = derive_organization_from_domain(domain)
        
        # Extract context from interactions (with max 20 emails)
        context = extract_recent_context(interactions_data, email, max_interactions=20)
        
        # Categorize organization
        org_category = categorize_organization(domain, organization, email)
        
        # Determine if Australian government
        is_australian_gov = org_category == 'Australian Government'
        
        # Create contact name from email (fallback)
        contact_name = email.split('@')[0].replace('.', ' ').title()
        
        # Compile summary record
        summary_record = {
            'contact_name': contact_name,
            'email': email,
            'domain': domain,
            'organization': organization,
            'organization_category': org_category,
            'is_australian_government': is_australian_gov,
            'interaction_count': context['interaction_count'],
            'engagement_level': context['engagement_level'],
            'first_contact': context['first_contact'],
            'last_contact': context['last_contact'],
            'interaction_summary': context['interaction_summary'],
            'recent_email_subjects': context['recent_subjects'],
            'relationship_indicators': context['relationship_indicators'],
            'sample_email_context': context['best_email_sample']
        }
        
        summary_data.append(summary_record)
    
    # Create DataFrame and save
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by interaction count (descending) then by engagement level
    engagement_order = {'Very High': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Minimal': 1, 'None': 0}
    summary_df['engagement_sort'] = summary_df['engagement_level'].map(engagement_order)
    summary_df = summary_df.sort_values(['interaction_count', 'engagement_sort'], ascending=[False, False])
    summary_df = summary_df.drop('engagement_sort', axis=1)
    
    # Save to CSV
    summary_df.to_csv(output_file, index=False)
    print(f"\nSaved focused summary to {output_file}")
    print(f"Total important contacts processed: {len(summary_df)}")
    print(f"Contacts with interactions: {len(summary_df[summary_df['interaction_count'] > 0])}")
    print(f"High engagement contacts: {len(summary_df[summary_df['engagement_level'].isin(['High', 'Very High'])])}")

@click.command()
@click.option('--important-contacts', default='important_contacts.txt', help='Important contacts text file')
@click.option('--interactions-file', default='output/contact_interactions.json', help='Interactions JSON file')
@click.option('--output-file', default='output/important_contacts_llm_summary.csv', help='Output summary CSV for important contacts')
def main(important_contacts, interactions_file, output_file):
    """Create focused LLM summary for important contacts with maximum context"""
    create_important_contacts_summary(important_contacts, interactions_file, output_file)

if __name__ == '__main__':
    main() 