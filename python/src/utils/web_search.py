import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger
import re
import html
from bs4 import BeautifulSoup


class WebSearch:
    """Utility for performing web searches and fetching web content.
    
    This class provides methods for searching the web using a search engine
    and fetching and parsing content from web pages.
    """
    
    def __init__(self, user_agent: Optional[str] = None):
        """Initialize the web search utility.
        
        Args:
            user_agent: Optional custom user agent string
        """
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        logger.debug(f"WebSearch initialized with user agent: {self.user_agent}")
    
    async def search(self, query: str, num_results: int = 5, search_region: str = "wt-wt") -> List[Dict[str, str]]:
        """Search the web using DuckDuckGo.
        
        Args:
            query: The search query
            num_results: Number of results to return (default: 5)
            search_region: Region code for search results (default: wt-wt for worldwide)
            
        Returns:
            List of search results with title, url, and snippet
        """
        try:
            # Use DuckDuckGo search
            encoded_query = query.replace(" ", "+")
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}&kl={search_region}"
            
            logger.info(f"Searching web for query: {query}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers={"User-Agent": self.user_agent}
                ) as response:
                    
                    if response.status != 200:
                        logger.error(f"Search request failed with status code: {response.status}")
                        return []
                    
                    html_content = await response.text()
                    
                    results = []
                    soup = BeautifulSoup(html_content, "html.parser")
                    result_elements = soup.select(".result")
                    
                    for i, result in enumerate(result_elements):
                        if i >= num_results:
                            break
                        
                        title_elem = result.select_one(".result__title")
                        url_elem = result.select_one(".result__url")
                        snippet_elem = result.select_one(".result__snippet")
                        
                        if title_elem and url_elem:
                            title = title_elem.get_text(strip=True)
                            url = url_elem.get_text(strip=True)
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet
                            })
                    
                    logger.info(f"Found {len(results)} search results")
                    return results
        except Exception as e:
            logger.error(f"Error during web search: {str(e)}")
            return []
    
    async def fetch_page_content(self, url: str, extract_text: bool = True) -> Dict[str, Any]:
        """Fetch content from a web page.
        
        Args:
            url: URL of the web page to fetch
            extract_text: Whether to extract readable text from the page (default: True)
            
        Returns:
            Dictionary containing page details and content
        """
        try:
            logger.info(f"Fetching web page content: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"User-Agent": self.user_agent}
                ) as response:
                    
                    if response.status != 200:
                        logger.error(f"Page fetch failed with status code: {response.status}")
                        return {
                            "success": False,
                            "url": url,
                            "status_code": response.status,
                            "error": f"HTTP status {response.status}"
                        }
                    
                    content_type = response.headers.get("Content-Type", "").lower()
                    if not content_type.startswith("text/html"):
                        logger.warning(f"Non-HTML content type: {content_type}")
                        return {
                            "success": False,
                            "url": url,
                            "status_code": response.status,
                            "error": f"Unsupported content type: {content_type}"
                        }
                    
                    html_content = await response.text()
                    
                    result = {
                        "success": True,
                        "url": url,
                        "status_code": response.status,
                        "html": html_content
                    }
                    
                    if extract_text:
                        text_content = self._extract_text_from_html(html_content)
                        result["text"] = text_content
                    
                    return result
        except Exception as e:
            logger.error(f"Error fetching page content: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text from HTML content.
        
        Args:
            html_content: HTML content to extract text from
            
        Returns:
            Extracted text content
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove script and style elements
            for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                script_or_style.extract()
            
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            # Collapse whitespace and remove blank lines
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {str(e)}")
            return ""
    
    async def search_and_fetch(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Search and fetch content from top results in one operation.
        
        Args:
            query: The search query
            num_results: Number of results to fetch content for (default: 3)
            
        Returns:
            List of search results with fetched content
        """
        search_results = await self.search(query, num_results=num_results)
        
        fetched_results = []
        for result in search_results:
            url = result.get("url")
            if url:
                page_content = await self.fetch_page_content(url)
                if page_content.get("success"):
                    fetched_results.append({
                        "title": result.get("title"),
                        "url": url,
                        "snippet": result.get("snippet"),
                        "content": page_content.get("text", "")
                    })
        
        logger.info(f"Fetched content for {len(fetched_results)} search results")
        return fetched_results