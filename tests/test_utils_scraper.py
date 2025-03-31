import pytest
import re
from urllib.parse import urlparse
from ttd.scraper.utils import extract_domain, extract_markdown_from_html

# Assume we are importing the functions from your module, e.g. `my_module`
# from my_module import extract_domain, extract_markdown_from_html

##############################################################################
# Tests for extract_domain
##############################################################################

@pytest.mark.parametrize("url,expected_domain", [
    ("http://example.com", "example.com"),
    ("https://example.com", "example.com"),
    ("http://www.example.com", "example.com"),
    ("https://www.example.com/path?query=123", "example.com"),
    ("http://subdomain.example.com/page", "subdomain.example.com"),
    ("http://www.subdomain.example.com", "subdomain.example.com"),
    ("http://www2.example.org", ".example.org"),  # we only strip "www."
    ("ftp://www.example.net", "example.net"),         # unusual scheme
    ("", ""),  # empty string
])
def test_extract_domain(url, expected_domain):
    from urllib.parse import urlparse
    parsed = extract_domain(url)
    assert parsed == expected_domain


##############################################################################
# Tests for extract_markdown_from_html
##############################################################################

def test_extract_markdown_from_html():

    html = """
    <html>
        <body>
        <p>First paragraph with a <a href="http://example.com">link</a> inside.</p>
        <p>Here is an image: <img src="http://example.com/image.png" alt="alt text"/></p>
        <h2>Another Heading</h2>
        <p>Second paragraph. 
            Some <b>bold text</b> and 
            a <i>line break</i>.
        </p>
        </body>
    </html>
    """

    result = extract_markdown_from_html(html)

    # Basic checks: ensure headings and paragraph text survive, minus HTML tags
    assert "First paragraph with a link inside." in result
    assert "Second paragraph." in result

    # Check the link text was preserved, but the actual URL is removed
    assert "link" in result
    assert "http://example.com" not in result

    # Check that the image alt text remains, but the URL doesn't
    assert "http://example.com/image.png" not in result

    # Check that bold/italic tags were stripped
    assert "bold text" in result
    assert "<b>" not in result
    assert "<i>" not in result