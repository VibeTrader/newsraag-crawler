import re

def clean_markdown(text: str) -> str:
    """
    Cleans markdown content to extract only the relevant news article
    while preserving structure and important information.
    """
    
    # First identify if this is a market/financial article with specific patterns
    is_financial_article = bool(re.search(r'(Natural Gas|market|trading|price|chart|consumption|export)', text, re.IGNORECASE))
    
    # Remove common navigation and promotional content
    navigation_patterns = [
        r'## Babypips \* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* Trading Systems \* Psychology \* Technical Analysis \* Trade Ideas \*',
        r'\* Ed Ponsi \* Wayne McDonell \* Brokers.*?Press Releases',
        r'MENU.*?COACHES',
        r'ASSETS.*?COACHES',
        r'LATEST NEWS.*?COACHES',
        r'Skip to main content.*?Newsletter',
        r'\* Ed Ponsi \* Wayne McDonell \* Brokers \* Brokers \* Broker Reviews \* Best of \d+ \* Trader Cashback \* Press Releases',
        r'!\[pepperstone-markets-limited \]\(.*?Pepperstone',
        r'ADVERTISEMENT.*?BELOW',
        r'SPONSORED.*?investment advice\.',
        r'Ad-free experience.*?Sign In',
        r'Daily actionable short-term strategies',
        r'Did this content help you\?.*?',
        r'About \*\*Dr\. Pipslow\*\*.*?$',
        r'Follow us on.*?$',
        r'Share:.*?$',
        r'Comments.*?$',
        r'Trade Today.*?$',
    ]
    
    # Remove unwanted content
    for pattern in navigation_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract article title and date for news articles
    title = ""
    date = ""
    
    title_match = re.search(r'# ([^\n]+)', text)
    if title_match:
        title = title_match.group(1).strip()
    
    date_match = re.search(r'NEWS \| (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})', text)
    if date_match:
        date = date_match.group(1).strip()
    
    # Clean up HTML tags and markdown formatting
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove image references but preserve captions
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'!([A-Z][^!]+)', r'\n\nImage: \1\n\n', text)  # Convert to image captions
    
    # Find the main article content based on article type
    if is_financial_article and (title_match or date_match):
        # For news articles like Natural Gas, extract content between title and end markers
        main_content_start = 0
        
        if title_match:
            main_content_start = title_match.end()
        
        # Find earliest end marker
        end_markers = [
            r'!\[pepperstone-markets-limited \]',
            r'Trade Today',
            r'Comments',
            r'Popular',
            r'About \*\*Dr\. Pipslow\*\*'
        ]
        
        main_content_end = len(text)
        for marker in end_markers:
            match = re.search(marker, text[main_content_start:], re.IGNORECASE)
            if match and main_content_start + match.start() < main_content_end:
                main_content_end = main_content_start + match.start()
        
        main_content = text[main_content_start:main_content_end].strip()
    else:
        # For advice articles like psychological journaling
        article_patterns = [
            r'Sure, keeping score.*?trading account\.',  # The psychological journal article
            r'## \d+\.\s+.*?(?=##(?!\s+\d+\.)|$)',      # Numbered sections
        ]
        
        main_content = text
        for pattern in article_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                main_content = " ".join(matches)
                break
    
    # Preserve headers and structure
    main_content = re.sub(r'## \*\*([^*]+)\*\*', r'\n\n## \1', main_content)  # Bold headers
    main_content = re.sub(r'##\s+(\d+\.\s+)', r'\n\n### \1', main_content)    # Numbered headers
    main_content = re.sub(r'##\s+([^#\n]+)', r'\n\n## \1', main_content)      # Regular headers
    
    # Preserve bullet points
    main_content = re.sub(r'^\s*\*\s+', '\n• ', main_content, flags=re.MULTILINE)
    
    # Clean URLs and references
    main_content = re.sub(r'https?://[^\s]+', '', main_content)
    main_content = re.sub(r'www\.[^\s]+', '', main_content)
    
    # Clean up whitespace
    main_content = re.sub(r'\s+', ' ', main_content)
    main_content = main_content.strip()
    
    # Restore paragraph breaks
    main_content = re.sub(r'(\. |\? |\! )([A-Z])', r'\1\n\n\2', main_content)
    
    # Format the final output
    result = ""
    if title:
        result += f"# {title}\n\n"
    if date:
        result += f"Date: {date}\n\n"
    result += main_content
    
    # Remove very short content
    if len(result) < 50:
        return ""
    
    return result