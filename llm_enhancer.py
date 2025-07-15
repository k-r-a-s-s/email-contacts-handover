#!/usr/bin/env python3
"""
LLM Contact Enhancer for ALLFED Handover
Uses LLM to analyze email content and provide context about relationships
"""

import json
import os
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import click
from tqdm import tqdm
from dotenv import load_dotenv
import requests

# Import LLM clients
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class ContactEnhancer:
    def __init__(self, output_dir: str = "output", llm_provider: str = "openai"):
        self.output_dir = Path(output_dir)
        self.llm_provider = llm_provider
        
        # Load environment variables
        load_dotenv()
        
        # Initialize LLM client
        self.client = None
        if llm_provider == "openai" and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
            else:
                print("Warning: OPENAI_API_KEY not found in environment")
        
        elif llm_provider == "openrouter":
            api_key = os.getenv("OPENROUTER_KEY")
            if api_key:
                self.client = "openrouter_client"  # Flag to indicate successful setup
                self.api_key = api_key
            else:
                print("Warning: OPENROUTER_KEY not found in environment")
        
        elif llm_provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
            else:
                print("Warning: ANTHROPIC_API_KEY not found in environment")
    
    def load_contacts_and_interactions(self) -> tuple[pd.DataFrame, Dict]:
        """Load contacts and interaction data"""
        contacts_file = self.output_dir / "important_contacts_llm_summary.csv"
        interactions_file = self.output_dir / "contact_interactions.json"
        
        if not contacts_file.exists():
            raise FileNotFoundError(f"Contacts file not found: {contacts_file}")
        
        if not interactions_file.exists():
            raise FileNotFoundError(f"Interactions file not found: {interactions_file}")
        
        # Load contacts
        contacts_df = pd.read_csv(contacts_file)
        
        # Load interactions
        with open(interactions_file, 'r') as f:
            interactions = json.load(f)
        
        return contacts_df, interactions
    
    def create_contact_analysis_prompt(self, contact: Dict, interactions: List[Dict]) -> str:
        """Create a prompt for analyzing a contact's relationship with ALLFED"""
        
        # Use the sample email context from our important contacts summary
        interaction_text = contact.get('sample_email_context', 'No email context available')
        
        # If no sample context, fall back to building from interactions
        if not interaction_text or interaction_text == 'No email context available':
            interaction_summaries = []
            for interaction in interactions[:5]:  # Limit to first 5 interactions
                interaction_summaries.append(
                    f"Date: {interaction['date']}\n"
                    f"Subject: {interaction['subject']}\n"
                    f"Content: {interaction['body_snippet'][:200]}...\n"
                )
            interaction_text = "\n---\n".join(interaction_summaries)
        
        prompt = f"""
Analyze this contact's relationship with ALLFED based on email interactions:

CONTACT INFORMATION:
Name: {contact.get('contact_name', contact.get('name', 'Unknown'))}
Email: {contact['email']}
Organization: {contact['organization']}
Domain: {contact['domain']}
Organization Category: {contact.get('organization_category', 'Unknown')}
Current Engagement Level: {contact.get('engagement_level', 'Unknown')}
Total Interactions: {contact['interaction_count']}
First Contact: {contact.get('first_contact', 'Unknown')}
Last Contact: {contact.get('last_contact', 'Unknown')}
Relationship Indicators: {contact.get('relationship_indicators', 'Unknown')}
Recent Email Subjects: {contact.get('recent_email_subjects', 'Unknown')}
Interaction Summary: {contact.get('interaction_summary', 'Unknown')}

EMAIL INTERACTIONS:
{interaction_text}

Please provide a structured analysis with the following information:

1. RELATIONSHIP_TYPE: (Choose one: Government Official, Academic/Researcher, NGO Representative, Industry Contact, Media, Other)

2. ENGAGEMENT_LEVEL: (Choose one: High - Regular collaboration/communication, Medium - Occasional meaningful contact, Low - Minimal/one-off contact)

3. KEY_TOPICS: List 2-3 main topics of discussion based on email subjects and content

4. RELATIONSHIP_DESCRIPTION: 2-3 sentence description of this person's role and relationship with ALLFED

5. HANDOVER_PRIORITY: (Choose one: High - Critical relationship to maintain, Medium - Important but not urgent, Low - Optional to maintain)

6. SUGGESTED_NEXT_STEPS: Brief suggestion for how successor should approach this relationship

Please format your response as JSON with these exact keys:
{{
    "relationship_type": "",
    "engagement_level": "",
    "key_topics": [],
    "relationship_description": "",
    "handover_priority": "",
    "suggested_next_steps": ""
}}
"""
        return prompt
    
    def analyze_contact_with_llm(self, contact: Dict, interactions: List[Dict]) -> Optional[Dict]:
        """Analyze a single contact using LLM"""
        if not self.client:
            return None
        
        prompt = self.create_contact_analysis_prompt(contact, interactions)
        
        try:
            if self.llm_provider == "openai":
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Using cost-effective model
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing professional relationships and email communications. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                content = response.choices[0].message.content
                
            elif self.llm_provider == "openrouter":
                # Direct API call to OpenRouter
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://allfed.info"
                }
                
                data = {
                    "model": "deepseek/deepseek-chat-v3-0324:free",
                    "messages": [
                        {"role": "system", "content": "You are an expert at analyzing professional relationships and email communications. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                else:
                    print(f"OpenRouter API error: {response.status_code} - {response.text}")
                    return None
                
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",  # Using cost-effective model
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text
            
            # Parse JSON response
            try:
                # First try direct parsing
                analysis = json.loads(content.strip())
                return analysis
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                try:
                    # Remove markdown code block markers
                    if '```json' in content:
                        # Extract content between ```json and ```
                        start = content.find('```json') + 7
                        end = content.find('```', start)
                        if end != -1:
                            json_content = content[start:end].strip()
                        else:
                            json_content = content[start:].strip()
                    elif content.strip().startswith('```') and content.strip().endswith('```'):
                        # Handle generic code blocks
                        lines = content.strip().split('\n')
                        json_content = '\n'.join(lines[1:-1])
                    else:
                        # Look for JSON block in the response
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            json_content = content[json_start:json_end]
                        else:
                            raise ValueError("No JSON found")
                    
                    analysis = json.loads(json_content)
                    return analysis
                except Exception as e:
                    print(f"Failed to parse JSON response for {contact['email']}: {e}")
                    print(f"Raw response: {content[:500]}...")
                    return None
                
        except Exception as e:
            print(f"Error analyzing contact {contact['email']}: {e}")
            return None
    
    def enhance_contacts(self, max_contacts: Optional[int] = None) -> None:
        """Enhance contacts with LLM analysis"""
        print("Loading important contacts and interactions...")
        contacts_df, interactions = self.load_contacts_and_interactions()
        
        if contacts_df.empty:
            print("No important contacts found to enhance")
            return
        
        # Already sorted by interaction count in the important contacts CSV
        if max_contacts:
            contacts_df = contacts_df.head(max_contacts)
        
        print(f"Enhancing {len(contacts_df)} important contacts with LLM analysis...")
        
        enhanced_contacts = []
        
        for _, contact in tqdm(contacts_df.iterrows(), total=len(contacts_df), desc="Analyzing contacts"):
            contact_dict = contact.to_dict()
            contact_interactions = interactions.get(contact['email'], [])
            
            # Get LLM analysis
            analysis = self.analyze_contact_with_llm(contact_dict, contact_interactions)
            
            # Combine original contact data with analysis
            enhanced_contact = contact_dict.copy()
            if analysis:
                enhanced_contact.update({
                    'llm_relationship_type': analysis.get('relationship_type', ''),
                    'llm_engagement_level': analysis.get('engagement_level', ''),
                    'llm_key_topics': ', '.join(analysis.get('key_topics', [])),
                    'llm_relationship_description': analysis.get('relationship_description', ''),
                    'llm_handover_priority': analysis.get('handover_priority', ''),
                    'llm_suggested_next_steps': analysis.get('suggested_next_steps', '')
                })
            else:
                # Add empty fields if analysis failed
                enhanced_contact.update({
                    'llm_relationship_type': 'Analysis Failed',
                    'llm_engagement_level': '',
                    'llm_key_topics': '',
                    'llm_relationship_description': '',
                    'llm_handover_priority': '',
                    'llm_suggested_next_steps': ''
                })
            
            enhanced_contacts.append(enhanced_contact)
        
        # Save enhanced contacts
        self.save_enhanced_contacts(enhanced_contacts)
    
    def save_enhanced_contacts(self, enhanced_contacts: List[Dict]) -> None:
        """Save enhanced contact data"""
        enhanced_df = pd.DataFrame(enhanced_contacts)
        
        # Sort by handover priority and engagement level
        priority_order = {'High': 3, 'Medium': 2, 'Low': 1}
        engagement_order = {'High': 3, 'Medium': 2, 'Low': 1}
        
        enhanced_df['priority_score'] = enhanced_df['llm_handover_priority'].map(priority_order).fillna(0)
        enhanced_df['engagement_score'] = enhanced_df['llm_engagement_level'].map(engagement_order).fillna(0)
        
        enhanced_df = enhanced_df.sort_values(['priority_score', 'engagement_score', 'interaction_count'], 
                                            ascending=[False, False, False])
        
        # Save to CSV
        csv_file = self.output_dir / "important_contacts_enhanced.csv"
        enhanced_df.to_csv(csv_file, index=False)
        print(f"Saved enhanced contacts to {csv_file}")
        
        # Save to Excel with formatting
        excel_file = self.output_dir / "important_contacts_enhanced.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            enhanced_df.to_excel(writer, sheet_name='Enhanced Contacts', index=False)
            
            # Create priority-based sheets
            high_priority = enhanced_df[enhanced_df['llm_handover_priority'] == 'High']
            if not high_priority.empty:
                high_priority.to_excel(writer, sheet_name='High Priority', index=False)
            
            medium_priority = enhanced_df[enhanced_df['llm_handover_priority'] == 'Medium']
            if not medium_priority.empty:
                medium_priority.to_excel(writer, sheet_name='Medium Priority', index=False)
        
        print(f"Saved enhanced contacts to {excel_file}")
        
        # Generate summary report
        self.generate_enhancement_report(enhanced_df)
    
    def generate_enhancement_report(self, enhanced_df: pd.DataFrame) -> None:
        """Generate a report on the enhanced contacts"""
        report_file = self.output_dir / "important_contacts_enhancement_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("ALLFED Contact Enhancement Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total contacts analyzed: {len(enhanced_df)}\n\n")
            
            # Priority breakdown
            f.write("HANDOVER PRIORITY BREAKDOWN\n")
            f.write("-" * 30 + "\n")
            priority_counts = enhanced_df['llm_handover_priority'].value_counts()
            for priority, count in priority_counts.items():
                f.write(f"{priority}: {count}\n")
            f.write("\n")
            
            # Relationship type breakdown
            f.write("RELATIONSHIP TYPE BREAKDOWN\n")
            f.write("-" * 30 + "\n")
            type_counts = enhanced_df['llm_relationship_type'].value_counts()
            for rel_type, count in type_counts.items():
                f.write(f"{rel_type}: {count}\n")
            f.write("\n")
            
            # High priority contacts
            high_priority = enhanced_df[enhanced_df['llm_handover_priority'] == 'High']
            if not high_priority.empty:
                f.write("HIGH PRIORITY CONTACTS FOR HANDOVER\n")
                f.write("-" * 35 + "\n")
                for _, contact in high_priority.iterrows():
                    f.write(f"\n{contact.get('contact_name', contact.get('name', 'Unknown'))} <{contact['email']}>\n")
                    f.write(f"Organization: {contact['organization']}\n")
                    f.write(f"Relationship: {contact['llm_relationship_description']}\n")
                    f.write(f"Key Topics: {contact['llm_key_topics']}\n")
                    f.write(f"Next Steps: {contact['llm_suggested_next_steps']}\n")
                    f.write("-" * 50 + "\n")
        
        print(f"Generated enhancement report: {report_file}")


@click.command()
@click.option('--output', default='output', help='Output directory with contact data')
@click.option('--provider', default='openai', type=click.Choice(['openai', 'anthropic', 'openrouter']), help='LLM provider')
@click.option('--max-contacts', type=int, help='Maximum number of contacts to analyze (for testing)')
def main(output: str, provider: str, max_contacts: Optional[int]):
    """Enhance extracted contacts with LLM analysis"""
    
    # Check if required files exist
    output_path = Path(output)
    if not output_path.exists():
        click.echo(f"Error: Output directory not found: {output}")
        return
    
    if not (output_path / "important_contacts_llm_summary.csv").exists():
        click.echo(f"Error: important_contacts_llm_summary.csv not found in {output}")
        click.echo("Please run the important contacts summary generation first.")
        return
    
    # Initialize enhancer
    enhancer = ContactEnhancer(output, provider)
    
    if not enhancer.client:
        click.echo(f"Error: Could not initialize {provider} client. Please check your API key.")
        if provider == 'openai':
            click.echo("Required environment variable: OPENAI_API_KEY")
        elif provider == 'anthropic':
            click.echo("Required environment variable: ANTHROPIC_API_KEY")
        elif provider == 'openrouter':
            click.echo("Required environment variable: OPENROUTER_KEY")
        return
    
    # Enhance contacts
    enhancer.enhance_contacts(max_contacts)
    
    click.echo("\nContact enhancement complete!")
    click.echo(f"Check the '{output}' directory for enhanced results.")


if __name__ == "__main__":
    main() 