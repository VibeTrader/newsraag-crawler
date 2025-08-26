import re

def clean_markdown(text: str) -> str:
a    """Enhanced content cleaning to improve similarity scores."""
    
    # Remove common site branding and ads
    patterns_to_remove = [
        r'Skip to main content.*?Newsletter\n',
        r'TRENDING:.*?\n',
        r'GET THE APP.*?\n',
        r'\* \|.*?\n',
        r'\*.*?\n',
        r';.*?\n',
        r'^\s*$\n',  # Remove empty lines
        
        # Remove site branding and ads
        r'investingLive\s+investingLive\s+investingLive\s+investingLive',
        r'ADVERTISEMENT\s*-\s*CONTINUE\s+READING\s+BELOW',
        r'\[!\[.*?\]\(.*?\)\]\(.*?\)',  # Remove markdown images
        r'\[.*?\]\(.*?\)',  # Remove markdown links
        r'https?://[^\s]+',  # Remove URLs
        r'www\.[^\s]+',  # Remove www URLs
        
        # Remove navigation elements
        r'##\s*\[.*?\]\(.*?\)',  # Remove markdown headers with links
        r'\* \[.*?\]\(.*?\)',  # Remove navigation links
        r'\[AnalysisPremium\].*?\[Learn\].*?\[School\].*?\[Community\]',
        
        # Remove common noise
        r'Share this article',
        r'Follow us on',
        r'Subscribe to',
        r'Get the latest',
        r'Read more',
        r'Continue reading',
        r'Click here',
        r'Learn more',
        
        # Remove HTML-like content
        r'<[^>]+>',  # Remove HTML tags
        r'&[a-zA-Z]+;',  # Remove HTML entities
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
    
    # Clean up whitespace and formatting
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove multiple consecutive newlines
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Remove leading/trailing whitespace
    
    # Remove very short lines (likely navigation)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) > 10:  # Keep lines with more than 10 characters
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    return text.strip()