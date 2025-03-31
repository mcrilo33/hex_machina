import re
from urllib.parse import urlparse
from main_content_extractor import MainContentExtractor

def _extract_domain_urllib(url):
    """
    Extracts the domain name from a URL using urllib.parse.

    Parameters:
    url (str): The URL string.

    Returns:
    str: The domain name.
    """
    parsed_url = urlparse(url)
    parsed_url = parsed_url.netloc
    parsed_url = re.sub(r'^www.', '', parsed_url)
    return parsed_url

extract_domain = _extract_domain_urllib

import re

def _clean_markdown(text):
    # Remove images but preserve alt text if present
    text = re.sub(r'!\[([^\]]*?)\]\(.*?\)', r'\1', text, flags=re.DOTALL)

    # Remove remaining links but keep the link text
    text = re.sub(r'\[([^\]]*?)\]\(.*?\)(\W)', r'\1\2', text, flags=re.DOTALL)

    # Fix dashes separated by line breaks (e.g., "-\nword" → "-word")
    text = re.sub(r'(-)\n(\w)', r'\1\2', text)

    # Merge broken lines that are not paragraph breaks
    text = re.sub(r'(\S)\n(?=\S)', r'\1 ', text)

    # Fix markdown bullet lists
    #text = re.sub(r'\s*\*\s*', r'\n* ', text)

    # Fix markdown numbered lists
    text = re.sub(r' +(\d+\.) +', r'\n\1 ', text)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove lines full of [ \*#\n]
    text = re.sub(r'\n[ \*#\n]*', r'\n', text, flags=re.DOTALL)

    # Normalize whitespace and line breaks
    text = re.sub(r'\n{2,}', '\n', text)         # Collapse multiple newlines
    text = re.sub(r'[ \t]+', ' ', text)          # Collapse multiple spaces/tabs

    return text.strip()


def extract_markdown_from_html(html):
    """
    Extracts the main content from an HTML string as markdown.

    Parameters:
    html (str): The HTML string.

    Returns:
    str: The extracted markdown content.
    """
    extracted = MainContentExtractor.extract(html, output_format="markdown")
    return _clean_markdown(extracted)