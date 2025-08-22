import re

def clean_markdown(text: str) -> str:
    # Remove the common header/navigation content
    patterns_to_remove = [
        r'Skip to main content.*?Newsletter\n',
        r'TRENDING:.*?\n',
        r'GET THE APP.*?\n',
        r'\* \|.*?\n',
        r'\*.*?\n',
        r';.*?\n',
        r'^\s*$\n'  # Remove empty lines
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Remove multiple consecutive newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()