"""
Web Scraper Tool
================

Extract content from web pages.
Uses HTTP requests with BeautifulSoup for parsing.
"""

from typing import Any, Dict, Optional
import httpx
from bs4 import BeautifulSoup
import structlog
import re

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class WebScraperTool(BaseTool):
    """Web scraper for extracting content from URLs.
    
    Uses HTTP requests (no JavaScript rendering) with BeautifulSoup
    for HTML parsing. Extracts main content, removing navigation
    and other boilerplate.
    
    Features:
    - Clean text extraction
    - Metadata parsing (title, description)
    - Content length limiting
    - Error handling for common issues
    """
    
    name = "web_scraper"
    description = (
        "Extract the main content from a web page URL. "
        "Returns the page title and cleaned text content. "
        "Use this to read the full content of a specific article or page."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the web page to scrape"
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum characters to return (default 5000)",
                "default": 5000
            }
        },
        "required": ["url"]
    }
    
    # Tags to remove (usually navigation/boilerplate)
    REMOVE_TAGS = [
        "script", "style", "nav", "header", "footer",
        "aside", "form", "iframe", "noscript"
    ]
    
    # Tags likely to contain main content
    CONTENT_TAGS = ["article", "main", "div.content", "div.article"]
    
    def __init__(self):
        """Initialize web scraper."""
        super().__init__()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
    
    async def execute(
        self,
        url: str,
        max_length: int = 5000,
        **kwargs
    ) -> ToolResult:
        """Scrape content from URL.
        
        Args:
            url: Web page URL
            max_length: Maximum content length
            
        Returns:
            ToolResult with extracted content
        """
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return ToolResult(
                success=False,
                error="Invalid URL: must start with http:// or https://"
            )
        
        logger.info(f"Scraping: {url}")
        
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            ) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type.lower():
                    return ToolResult(
                        success=False,
                        error=f"Not an HTML page: {content_type}"
                    )
                
                html = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html, "lxml")
            
            # Extract metadata
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            
            # Remove unwanted tags
            for tag in self.REMOVE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Try to find main content
            content = self._extract_main_content(soup)
            
            # Clean and truncate
            content = self._clean_text(content)
            if len(content) > max_length:
                content = content[:max_length] + "...[truncated]"
            
            # Build observation
            observation = f"Title: {title}\n\n"
            if description:
                observation += f"Description: {description}\n\n"
            observation += f"Content:\n{content}"
            
            return ToolResult(
                success=True,
                data=observation,
                sources=[{
                    "id": 1,
                    "title": title,
                    "url": url,
                    "snippet": description or content[:200]
                }],
                metadata={
                    "url": url,
                    "title": title,
                    "content_length": len(content)
                }
            )
            
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                error=f"HTTP error {e.response.status_code}: {e}"
            )
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                error=f"Request failed: {e}"
            )
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return ToolResult(
                success=False,
                error=f"Scraping failed: {e}"
            )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]
        
        # Fall back to <title>
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        return "Untitled"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description."""
        # Try og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"]
        
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]
        
        return ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page."""
        # Try common content containers
        for selector in ["article", "main", "[role='main']", ".content", ".article", "#content"]:
            content = soup.select_one(selector)
            if content:
                return content.get_text(separator="\n", strip=True)
        
        # Fall back to body
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)
        
        return soup.get_text(separator="\n", strip=True)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove very short lines (likely navigation remnants)
        lines = text.split('\n')
        lines = [line for line in lines if len(line.strip()) > 20 or not line.strip()]
        
        return '\n'.join(lines).strip()
