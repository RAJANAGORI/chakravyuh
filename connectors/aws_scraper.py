import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from tqdm import tqdm
from datetime import datetime
from utils.url_utils import same_domain, canonicalize
import concurrent.futures
# from utils.tokenizer import split_text_by_tokens


USER_AGENT = "RAG-Scraper/1.0 (+https://your-site.example) RajaNagori-contact"
REQUEST_SLEEP = 0.6  # seconds between requests (tune politely)
MAX_PAGES = 5      # set to an int to limit crawl for testing
RETRY = 2

class AWSSiteScraper:
    def __init__(self, base_dir, start_urls, max_workers=None):
        """
        start_urls: list of dicts: [{"name": "s3", "url": "https://docs.aws.amazon.com/s3/"} ...]
        """
        self.base_dir = base_dir
        self.start_urls = start_urls
        self.max_workers = max_workers
        os.makedirs(self.base_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, url):
        for attempt in range(RETRY + 1):
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                if attempt < RETRY:
                    time.sleep(1 + attempt)
                    continue
                raise

    def extract_links(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # avoid mailto: javascript: and anchors-only
            if href.startswith("mailto:") or href.startswith("javascript:") or href.startswith("#"):
                continue
            full = canonicalize(base_url, href)
            if same_domain(base_url, full):
                links.add(full.split('#')[0])  # drop fragment
        return links

    def slug_from_url(self, url):
        p = urlparse(url)
        # create safe slug for files
        slug = re.sub(r'[^A-Za-z0-9\-_\.]', '_', p.path.strip("/"))
        if not slug:
            slug = "index"
        return slug

    def split_into_chunks(self, html_text):
        """
        Return list of chunks: each chunk is dict {chunk_id, heading, text}
        Splits by heading tags; if no headings present, return a single chunk.
        """
        soup = BeautifulSoup(html_text, "html.parser")

        # Remove scripts/styles
        for s in soup(["script", "style", "noscript"]):
            s.decompose()

        body = soup.body or soup

        # Find all headings and the following content until next heading
        headings = body.find_all(re.compile("^h[1-6]$"))
        if not headings:
            # fallback: get main text
            text = body.get_text(separator="\n").strip()
            if not text:
                text = ""
            return [{"chunk_id": "0", "heading": None, "text": text}]

        chunks = []
        for idx, h in enumerate(headings):
            heading_text = h.get_text(separator=" ").strip()
            # gather siblings until next heading of same or higher level
            parts = []
            for sib in h.next_siblings:
                if getattr(sib, "name", None) and re.match("^h[1-6]$", sib.name, re.I):
                    break
                parts.append(getattr(sib, "get_text", lambda sep="": str(sib))(separator="\n"))
            chunk_text = heading_text + "\n" + "\n".join(parts)
            chunks.append({
                "chunk_id": str(idx),
                "heading": heading_text,
                "text": chunk_text.strip()
            })
        return chunks

    def save_page_files(self, service_dir, slug, url, html, chunks):
        os.makedirs(service_dir, exist_ok=True)
        html_path = os.path.join(service_dir, f"{slug}.html")
        json_path = os.path.join(service_dir, f"{slug}.json")
        ndjson_path = os.path.join(service_dir, f"{slug}.ndjson")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # metadata for each chunk
        docs = []
        timestamp = datetime.utcnow().isoformat()
        if all(len(c["text"].strip()) == 0 for c in chunks):
            # Skip pages without meaningful text
            return None, None, None, 0
        for c in chunks:
            doc = {
                "doc_id": f"aws-{slug}-{c['chunk_id']}",
                "text": c["text"],
                "metadata": {
                    "source": "AWS Docs",
                    "service_page": slug,
                    "heading": c["heading"],
                    "url": url,
                    "scraped_at": timestamp
                }
            }
            docs.append(doc)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)

        with open(ndjson_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        return html_path, json_path, ndjson_path, len(docs)

    def crawl_service(self, service_name, start_url):
        service_dir = os.path.join(self.base_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)

        to_visit = [start_url]
        visited = set()
        page_count = 0

        pbar = tqdm(desc=f"Scraping {service_name}", unit="pages")
        while to_visit:
            url = to_visit.pop(0)
            if url in visited:
                continue
            if MAX_PAGES and page_count >= MAX_PAGES:
                break
            try:
                html = self.fetch(url)
            except Exception as e:
                print(f"ERROR fetching {url}: {e}")
                visited.add(url)
                continue

            slug = self.slug_from_url(url)
            chunks = self.split_into_chunks(html)
            html_path, json_path, ndjson_path, n_chunks = self.save_page_files(service_dir, slug, url, html, chunks)
            page_count += 1
            visited.add(url)
            pbar.update(1)
            pbar.set_postfix({"page": slug, "chunks": n_chunks})

            # extract and queue links
            links = self.extract_links(url, html)
            for l in links:
                if l not in visited and l not in to_visit:
                    to_visit.append(l)

            time.sleep(REQUEST_SLEEP)
        pbar.close()
        print(f"✅ Finished scraping {service_name}: {page_count} pages saved at {service_dir}")

    # def split_into_chunks(self, html_text, model="gpt-3.5-turbo", chunk_size=500, overlap=50):
    #     """
    #     First split by headings, then sub-chunk by token size.
    #     Returns list of {chunk_id, heading, text}
    #     """
    #     soup = BeautifulSoup(html_text, "html.parser")

    #     # Remove scripts/styles
    #     for s in soup(["script", "style", "noscript"]):
    #         s.decompose()

    #     body = soup.body or soup
    #     headings = body.find_all(re.compile("^h[1-6]$"))

    #     chunks = []
    #     if not headings:
    #         # fallback single chunk
    #         text = body.get_text(separator="\n").strip()
    #         subchunks = split_text_by_tokens(text, model, chunk_size, overlap)
    #         for i, sub in enumerate(subchunks):
    #             chunks.append({
    #                 "chunk_id": f"0-{i}",
    #                 "heading": None,
    #                 "text": sub
    #             })
    #         return chunks

    #     for idx, h in enumerate(headings):
    #         heading_text = h.get_text(separator=" ").strip()
    #         parts = []
    #         for sib in h.next_siblings:
    #             if getattr(sib, "name", None) and re.match("^h[1-6]$", sib.name, re.I):
    #                 break
    #             parts.append(getattr(sib, "get_text", lambda sep="": str(sib))(separator="\n"))
    #         chunk_text = (heading_text + "\n" + "\n".join(parts)).strip()

    #         subchunks = split_text_by_tokens(chunk_text, model, chunk_size, overlap)
    #         for i, sub in enumerate(subchunks):
    #             chunks.append({
    #                 "chunk_id": f"{idx}-{i}",
    #                 "heading": heading_text,
    #                 "text": sub
    #             })
    #     return chunks


    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers or len(self.start_urls)) as executor:
            futures = []
            for s in self.start_urls:
                name = s["name"]
                url = s["url"]
                print(f"Starting crawl for {name} -> {url}")
                futures.append(executor.submit(self.crawl_service, name, url))
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error during crawl: {e}")