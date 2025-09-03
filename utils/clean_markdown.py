import re

def clean_markdown(text: str) -> str:
    """Enhanced content cleaning to improve similarity scores while preserving market data."""
    
    # First remove all HTML tags and clean up basic formatting
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)
    
    # Keep these market-related terms and their content
    market_data_patterns = [
        r'Technical analysis:.*?(?=##|$)',  # Keep technical analysis section
        r'Market movers:.*?(?=##|$)',       # Keep market movers section
        r'\*\*([^*]+)\*\*',                 # Keep bold text content
        r'RSI.*?(?=\.|$)',                  # Keep RSI analysis
        r'MACD.*?(?=\.|$)',                 # Keep MACD analysis
        r'support.*?(?=\.|$)',              # Keep support levels
        r'resistance.*?(?=\.|$)',           # Keep resistance levels
        r'[0-9]+(?:\.[0-9]+)?%',           # Keep percentage values
        r'\$[0-9]+(?:\.[0-9]+)?',          # Keep price values
    ]
    
    # Store market data sections
    preserved_sections = []
    for pattern in market_data_patterns:
        matches = re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        for match in matches:
            preserved_sections.append((match.start(), match.end(), match.group(0)))
    
    # Remove navigation and promotional content
    navigation_patterns = [
        # Navigation and headers
        r'## Babypips \* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* Trading Systems \* Psychology \* Technical Analysis \* Trade Ideas \*',
        r'\* Ed Ponsi \* Wayne McDonell \* Brokers.*?Press Releases',
        r'MENU.*?COACHES',
        r'ASSETS.*?COACHES',
        r'LATEST NEWS.*?COACHES',
        r'Skip to main content.*?Newsletter',
        
        # Advertisements and promotions
        r'ADVERTISEMENT.*?BELOW',
        r'SPONSORED.*?investment advice\.',
        r'Ad-free experience.*?Sign In',
        r'Daily actionable short-term strategies',
        r'High-impact economic event trading guides',
        r'Unlimited Access access to MarketMilk',
        r'This Article Is For Premium Members Only',
        r'Become a Premium member.*?Plus More!',
        
        # Social and sharing
        r'Share:.*?investment advice\.',
        r'Share this article',
        r'Follow us on',
        r'Subscribe to',
        r'Get the latest',
        
        # Legal and disclaimers
        r'Information on these pages.*?investment advice\.',
        r'Risk Warning.*?investment advice\.',
        r'CFDs are complex instruments.*?investment advice\.',
        r'Forex trading involves significant risk.*?investors\.',
        r'Copyright.*?All rights reserved',
        
        # UI elements
        r'Plus More!',
        r'See what else is included!',
        r'Already a Premium member\?',
        r'Sign In',
        r'Partner Center',
        r'TRENDING:.*?',
        r'GET THE APP.*?',
        r'Read more',
        r'Continue reading',
        r'Click here',
        r'Learn more',
        r'View Menu',
        r'Try It Out!',
        
        # Tools and features
        r'Risk-On / Risk-Off Meter',
        r'Correlation Calculator',
        r'Learn Forex',
        r'Forex Tools',
        
        # Links and images
        r'\[ Trade Today \]',
        r'https://ad\.doubleclick\.net.*?',
        r'!\[pepperstone-markets-limited \]\(',
        
        # Language options
        r'Translate English.*?Traditional Chinese\)',
        r'English.*?Traditional Chinese\)',
        r'1\. English.*?18\. 繁體中文 \(Traditional Chinese\)',
    ]
    
    # Remove unwanted content
    for pattern in navigation_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up whitespace first pass
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Navigation markers for content cutoff
    navigation_markers = [
        'ADVERTISEMENT',
        'Broker Reviews',
        'Press Releases',
        'Partner Center',
        'Sign In',
        'Try It Out',
        'Plus More',
        'Already a Premium member?',
        'Share this article',
        'Copyright',
        'Learn Forex',
        'Risk Warning',
        'CFDs are complex',
    ]
    
    # Find earliest navigation marker and cut text there
    earliest_marker_pos = len(text)
    for marker in navigation_markers:
        pos = text.find(marker)
        if pos != -1 and pos < earliest_marker_pos:
            earliest_marker_pos = pos
    
    if earliest_marker_pos < len(text):
        text = text[:earliest_marker_pos]
    
    # Restore preserved market data sections
    preserved_sections.sort(key=lambda x: x[0])
    final_text_parts = []
    last_end = 0
    
    # Add main content
    if text.strip():
        final_text_parts.append(text.strip())
    
    # Add preserved sections
    for _, _, content in preserved_sections:
        if content.strip():
            final_text_parts.append(content.strip())
    
    # Join all parts
    result = ' '.join(final_text_parts)
    
    # Final cleanup
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()
    
    # Remove very short content
    if len(result) < 50:
        return ""
    
    return result