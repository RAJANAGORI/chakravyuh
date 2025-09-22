# utils/url_utils.py
from urllib.parse import urlparse, urljoin

def same_domain(base_url, other_url):
    b = urlparse(base_url)
    o = urlparse(other_url)
    return (b.scheme in ("http","https")) and (o.scheme in ("http","https")) and (b.netloc == o.netloc)

def canonicalize(base, link):
    return urljoin(base, link)