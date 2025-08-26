import re

def clean_markdown(text: str) -> str:
    """Enhanced content cleaning to improve similarity scores."""
    
    # First, try to extract only the actual article content
    # Look for content that starts with actual article text and ends before navigation
    
    # Remove all HTML tags completely
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove all markdown links and images
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)
    
    # Remove all navigation and site branding - be very aggressive
    navigation_patterns = [
        # Specific patterns from the actual data
        r'## Babypips \* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* AnalysisPremium \* News \* Trading \* Crypto \*',
        r'\* Trading Systems \* Psychology \* Technical Analysis \* Trade Ideas \*',
        r'\* Forex Glossary \*\*Forexpedia\*\*.*?View Quiz Library \*\(',
        r'\* Learn Crypto \* Crypto Guides.*?Start Learning \*\(',
        r'About \*\*.*?More from.*?',
        r'TRADE NOW \*',
        r'\* How to Trade Forex.*?Twitter',
        r'Babypips helps new traders learn.*?Privacy Manager',
        r'MENU.*?COACHES',
        r'ASSETS.*?COACHES',
        r'LATEST NEWS.*?COACHES',
        r'EDITORIAL SELECTION.*?COACHES',
        r'TOP EVENTS.*?COACHES',
        r'SECTIONS.*?COACHES',
        r'MOST POPULAR.*?COACHES',
        r'Share:.*?investment advice\.',
        r'Information on these pages.*?investment advice\.',
        r'FXStreet.*?investment advice\.',
        r'Sponsor.*?investment advice\.',
        r'Risk Warning.*?investment advice\.',
        r'CFDs are complex instruments.*?investment advice\.',
        r'Forex trading and trading.*?investment advice\.',
        r'Recommended content.*?investment advice\.',
        r'Editors\' Picks.*?investment advice\.',
        r'Premium.*?investment advice\.',
        r'AI 2\.0.*?investment advice\.',
        r'SPONSORED.*?investment advice\.',
        r'Forex MAJORS.*?investment advice\.',
        r'Cryptocurrencies.*?investment advice\.',
        r'Signatures.*?investment advice\.',
        r'Best Brokers.*?investment advice\.',
        r'English ©2025.*?investment advice\.',
        r'Ad-free experience.*?Sign In',
        r'Daily actionable short-term strategies',
        r'High-impact economic event trading guides',
        r'Unlimited Access access to MarketMilk',
        r'Plus More!',
        r'See what else is included!',
        r'Already a Premium member\?',
        r'Sign In',
        r'Partner Center',
        r'Skip to main content.*?Newsletter',
        r'TRENDING:.*?',
        r'GET THE APP.*?',
        r'Share this article',
        r'Follow us on',
        r'Subscribe to',
        r'Get the latest',
        r'Read more',
        r'Continue reading',
        r'Click here',
        r'Learn more',
        r'View Menu',
        r'Risk-On / Risk-Off Meter',
        r'Correlation Calculator',
        r'Learn Forex',
        r'Forex Tools',
        r'Company',
        r'Copyright.*?All rights reserved',
        r'This Article Is For Premium Members Only',
        r'Become a Premium member.*?Plus More!',
        r'Try It Out!',
        r'Based on client assets.*?CFTC',
        r'Forex trading involves significant risk.*?investors\.',
        r'\[ Trade Today \]',
        r'https://ad\.doubleclick\.net.*?',
        r'Translate English.*?Traditional Chinese\)',
        r'English.*?Traditional Chinese\)',
        r'1\. English.*?18\. 繁體中文 \(Traditional Chinese\)',
    ]
    
    for pattern in navigation_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Cut off content at the first sign of navigation
    navigation_markers = [
        '## Babypips',
        '* AnalysisPremium',
        '* Trading Systems',
        '* Forex Glossary',
        'About **',
        'TRADE NOW',
        'Babypips helps new traders learn',
        'MENU',
        'ASSETS',
        'LATEST NEWS',
        'Share:',
        'Information on these pages',
        'FXStreet',
        'Sponsor',
        'Risk Warning',
        'CFDs are complex instruments',
        'Forex trading and trading',
        'Recommended content',
        'Editors\' Picks',
        'Premium',
        'AI 2.0',
        'SPONSORED',
        'Forex MAJORS',
        'Cryptocurrencies',
        'Signatures',
        'Best Brokers',
        'English ©2025',
        'Ad-free experience',
        'Daily actionable short-term strategies',
        'High-impact economic event trading guides',
        'Unlimited Access access to MarketMilk',
        'Plus More!',
        'See what else is included!',
        'Already a Premium member?',
        'Sign In',
        'Partner Center',
        'Skip to main content',
        'TRENDING:',
        'GET THE APP',
        'Share this article',
        'Follow us on',
        'Subscribe to',
        'Get the latest',
        'Read more',
        'Continue reading',
        'Click here',
        'Learn more',
        'View Menu',
        'Risk-On / Risk-Off Meter',
        'Correlation Calculator',
        'Learn Forex',
        'Forex Tools',
        'Company',
        'Copyright',
        'This Article Is For Premium Members Only',
        'Become a Premium member',
        'Try It Out!',
        'Based on client assets',
        'Forex trading involves significant risk',
        '[ Trade Today ]',
        'https://ad.doubleclick.net',
        'Translate English',
        'English',
        '1. English',
    ]
    
    # Find the earliest navigation marker and cut the text there
    earliest_marker_pos = len(text)
    for marker in navigation_markers:
        pos = text.find(marker)
        if pos != -1 and pos < earliest_marker_pos:
            earliest_marker_pos = pos
    
    if earliest_marker_pos < len(text):
        text = text[:earliest_marker_pos]
    
    # Clean up whitespace again
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove very short content (likely just noise)
    if len(text) < 50:
        return ""
    
    return text