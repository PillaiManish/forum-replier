"""Web crawler for documentation sites with prefix-scoped crawling."""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Generator
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class CrawledPage:
    """A crawled documentation page."""
    url: str
    title: str
    content: str


class DocsCrawler:
    """Crawl documentation sites with prefix-scoped URL filtering."""
    
    def __init__(self, base_url: str, max_pages: int = 500, max_depth: int = 5):
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.max_depth = max_depth
        
        # Parse base URL for prefix scoping
        parsed = urlparse(self.base_url)
        self.base_domain = parsed.netloc
        self.base_path_prefix = parsed.path.rstrip("/") or "/"
        
        self.visited: set[str] = set()
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "ForumReplierBot/1.0"}
        )
    
    def crawl(self) -> Generator[CrawledPage, None, None]:
        """Crawl the documentation site starting from base_url."""
        console.print(f"[blue]Starting crawl:[/blue] {self.base_url}")
        console.print(f"[blue]Prefix scope:[/blue] {self.base_path_prefix}")
        
        yield from self._crawl_recursive(self.base_url, depth=0)
        
        console.print(f"[green]Crawl complete:[/green] {len(self.visited)} pages")
    
    def _crawl_recursive(self, url: str, depth: int) -> Generator[CrawledPage, None, None]:
        """Recursively crawl pages."""
        if depth > self.max_depth:
            return
        
        if len(self.visited) >= self.max_pages:
            return
        
        # Normalize URL
        url = url.split("#")[0].rstrip("/")
        
        if url in self.visited:
            return
        
        if not self._is_valid_url(url):
            return
        
        self.visited.add(url)
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            # Only process HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                return
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)
            
            # Extract main content
            content = self._extract_content(soup)
            
            if content.strip():
                console.print(f"  [dim]Crawled ({len(self.visited)}/{self.max_pages}):[/dim] {url[:80]}")
                yield CrawledPage(url=url, title=title, content=content)
            
            # Extract and follow links
            links = self._extract_links(soup, url)
            for link in links:
                yield from self._crawl_recursive(link, depth + 1)
                
        except Exception as e:
            console.print(f"  [red]Error crawling {url}:[/red] {str(e)[:50]}")
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling (same domain + prefix scope)."""
        try:
            parsed = urlparse(url)
            
            # Must be same domain
            if parsed.netloc != self.base_domain:
                return False
            
            # Must start with base path prefix (prefix-scoped crawling)
            url_path = parsed.path.rstrip("/") or "/"
            if not url_path.startswith(self.base_path_prefix):
                return False
            
            # Skip non-doc extensions
            skip_extensions = {".pdf", ".zip", ".tar", ".gz", ".png", ".jpg", ".gif", ".svg", ".css", ".js"}
            if any(url_path.lower().endswith(ext) for ext in skip_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from HTML."""
        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find(class_=["content", "main-content", "documentation", "docs-content"]) or
            soup.find("div", {"role": "main"}) or
            soup.body
        )
        
        if not main_content:
            return ""
        
        # Get text with some structure
        text_parts = []
        for element in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "code"]):
            text = element.get_text(separator=" ", strip=True)
            if text:
                if element.name.startswith("h"):
                    text_parts.append(f"\n## {text}\n")
                elif element.name == "pre":
                    text_parts.append(f"\n```\n{text}\n```\n")
                else:
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        """Extract internal links from the page."""
        links = []
        
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            
            # Skip empty, anchors, and special links
            if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(current_url, href)
            
            # Remove fragment
            absolute_url = absolute_url.split("#")[0].rstrip("/")
            
            if self._is_valid_url(absolute_url) and absolute_url not in self.visited:
                links.append(absolute_url)
        
        return links
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()


