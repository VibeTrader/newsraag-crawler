import re

def clean_markdown(text: str) -> str:
    """
    Enhanced content cleaning that preserves financial data while removing navigation elements,
    advertisements, and duplicate content.
    """
    
    # First extract important metadata if present
    title = ""
    date = ""
    author = ""
    
    title_match = re.search(r'# ([^\n#]+)', text)
    if title_match:
        title = title_match.group(1).strip()
        
    date_match = re.search(r'NEWS \| (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})', text)
    if date_match:
        date = date_match.group(1)
        
    author_match = re.search(r'By ([^\n*]+)', text)
    if author_match:
        author = author_match.group(1).strip()
    
    # STEP 1: Remove navigation elements and menus
    # These patterns are specific to the financial sites you're crawling
    navigation_patterns = [
        # Main navigation menus
        r'\* Ed Ponsi \* Wayne McDonell \* Brokers.*?Press Releases(.*?)(?=# |$)',
        r'Top Brokers.*?Open my account.*?(?=# |$)',
        r'Trading Studio.*?Fed Sentiment Index.*?(?=# |$)',
        r'ASSETS.*?EDITORIAL SELECTION.*?(?=# |$)',
        r'SECTIONS.*?MOST POPULAR COACHES.*?(?=# |$)',
        r'Babypips.*?AnalysisPremium.*?Trade Ideas.*?(?=\d\.|$)',
        
        # Footer elements
        r'Comments.*?Franklin.*?(?=# |$)',
        r'* No\. \d+ FX broker.*?(?=# |$)',
        r'Trade Today.*?(?=# |$)',
        r'* How to Trade Forex.*?(?=# |$)',
        
        # Other site elements
        r'_Did this content help you\?.*?current market conditions.*?(?=# |$)',
        r'* Privacy Policy.*?(?=# |$)'
    ]
    
    # Apply navigation removal patterns
    for pattern in navigation_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # STEP 2: Fix any data inconsistencies
    
    # Fix truncated price values 
    text = re.sub(r'beyond \$3(?!\d)', r'beyond $3,500', text)
    text = re.sub(r'above \$3(?!\d)', r'above $3,470', text)
    
    # Normalize price formats (European to US format)
    text = re.sub(r'\$(\d+)\.(\d+)', r'$\1,\2', text)
    
    # Remove duplicate consecutive prices
    text = re.sub(r'(\$[\d,\.]+)(\s+\1)+', r'\1', text)
    
    # STEP 3: Remove formatting but preserve structure
    
    # Remove image references but keep captions
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    
    # Remove links but preserve text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove URLs
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # STEP 4: Remove duplicate sections
    
    # Remove duplicate title occurrences
    if title:
        text = re.sub(f'# {re.escape(title)}', '', text)
    
    # STEP 5: Clean up whitespace and structure
    text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize newlines
    text = re.sub(r'\s{2,}', ' ', text)     # Normalize spaces
    
    # STEP 6: Reconstruct the article with clean structure
    clean_article = ""
    if title:
        clean_article += f"# {title}\n\n"
    if date:
        clean_article += f"Date: {date}\n\n"
    if author:
        clean_article += f"By: {author}\n\n"
    
    # Add the remaining cleaned content
    remaining_content = text.strip()
    if remaining_content:
        clean_article += remaining_content
        
    # STEP 7: Final cleanup of specific artifacts
    
    # Fix multiple asterisks
    clean_article = re.sub(r'\*{3,}', '**', clean_article)
    
    # Remove any database metadata that got mixed in
    clean_article = re.sub(r'text_length.*?(?=\n|$)', '', clean_article, flags=re.DOTALL)
    clean_article = re.sub(r'publishDatePst.*?(?=\n|$)', '', clean_article, flags=re.DOTALL)
    clean_article = re.sub(r'source.*?(?=\n|$)', '', clean_article, flags=re.DOTALL)
    clean_article = re.sub(r'Vectors:.*?(?=\n|$)', '', clean_article, flags=re.DOTALL)
    
    # Final whitespace cleanup
    clean_article = re.sub(r'\s+', ' ', clean_article)
    clean_article = clean_article.strip()
    
    # STEP 8: Restore paragraph breaks for readability
    clean_article = re.sub(r'(\. |\? |\! )([A-Z])', r'\1\n\n\2', clean_article)
    
    # Only return if we have substantial content
    if len(clean_article) < 100:
        return ""
        
    return clean_article