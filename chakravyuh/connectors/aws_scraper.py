"""AWS documentation scraper."""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

from chakravyuh.core.logging import logger


class AWSSiteScraper:
    """Scraper for AWS documentation sites."""

    def __init__(
        self,
        base_dir: str = "./data/raw",
        start_urls: List[Dict[str, str]] = None,
        max_workers: int = 4,
        delay: float = 1.0,
    ):
        """
        Initialize AWS scraper.

        Args:
            base_dir: Base directory to save scraped files
            start_urls: List of dicts with 'name' and 'url' keys
            max_workers: Number of parallel workers (not used in basic implementation)
            delay: Delay between requests in seconds
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.start_urls = start_urls or []
        self.max_workers = max_workers
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.scraped_urls = set()

    def _get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            time.sleep(self.delay)  # Be respectful
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content from page."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Try to find main content area
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", class_=lambda x: x and "content" in x.lower()) or
            soup.find("body")
        )

        if main_content:
            return main_content.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract relevant links from page."""
        links = []
        base_domain = urlparse(base_url).netloc

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)

            # Only include links to same domain
            if urlparse(full_url).netloc == base_domain:
                # Filter for documentation pages
                if any(path in full_url for path in ["/latest/", "/userguide/", "/developerguide/"]):
                    links.append(full_url)

        return links

    def _save_page(self, url: str, content: str, metadata: Dict[str, Any], service_name: str):
        """Save scraped page to file with path traversal protection."""
        # Sanitize service_name to prevent path traversal
        safe_service_name = "".join(c for c in service_name if c.isalnum() or c in ('-', '_'))
        if not safe_service_name:
            logger.error(f"Invalid service name: {service_name}, using 'unknown'")
            safe_service_name = "unknown"
        
        # Create service directory
        service_dir = self.base_dir / safe_service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename from URL to prevent path traversal
        url_path = urlparse(url).path.strip("/").replace("/", "_")
        # Remove any remaining dangerous characters
        safe_filename = "".join(c for c in url_path if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename or len(safe_filename) > 255:
            safe_filename = "index"
        
        # Ensure filename doesn't start with . to prevent hidden files
        if safe_filename.startswith('.'):
            safe_filename = "index"
        
        filename = f"{safe_filename}.json"
        filepath = service_dir / filename

        # Resolve paths to prevent directory traversal
        try:
            resolved_filepath = filepath.resolve()
            resolved_service_dir = service_dir.resolve()
            
            # Ensure the resolved path is within the service directory
            if not str(resolved_filepath).startswith(str(resolved_service_dir)):
                logger.error(f"Path traversal detected: {filepath}")
                raise ValueError(f"Path traversal attempt detected: {filepath}")
        except (OSError, ValueError) as e:
            logger.error(f"Invalid file path: {e}")
            # Fallback to safe default
            filepath = service_dir / "index.json"

        data = {
            "url": url,
            "content": content,
            "metadata": metadata,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved: {filepath}")

    def scrape_url(self, url: str, service_name: str, max_depth: int = 2, current_depth: int = 0):
        """Scrape a single URL and follow links."""
        if url in self.scraped_urls or current_depth > max_depth:
            return

        self.scraped_urls.add(url)
        logger.info(f"Scraping [{current_depth}]: {url}")

        soup = self._get_page_content(url)
        if not soup:
            return

        # Extract content
        content = self._extract_text(soup)
        title = soup.find("title")
        title_text = title.get_text() if title else ""

        metadata = {
            "url": url,
            "title": title_text,
            "service": service_name,
            "depth": current_depth,
        }

        # Save page
        self._save_page(url, content, metadata, service_name)

        # Follow links if not at max depth
        if current_depth < max_depth:
            links = self._extract_links(soup, url)
            for link in links[:10]:  # Limit to 10 links per page
                if link not in self.scraped_urls:
                    self.scrape_url(link, service_name, max_depth, current_depth + 1)

    def run(self):
        """Run the scraper for all configured services."""
        logger.info(f"Starting AWS scraper for {len(self.start_urls)} services")

        for service in self.start_urls:
            name = service.get("name", "unknown")
            url = service.get("url")

            if not url:
                logger.warning(f"Skipping service {name}: no URL provided")
                continue

            logger.info(f"Scraping service: {name} from {url}")
            self.scrape_url(url, name, max_depth=1)  # Start with depth 1 to limit scope

        logger.info(f"✅ Scraping complete. Scraped {len(self.scraped_urls)} pages")
