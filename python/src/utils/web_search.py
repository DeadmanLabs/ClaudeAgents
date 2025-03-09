import aiohttp
import asyncio
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from loguru import logger
import re
import html
from bs4 import BeautifulSoup
import json

from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain.tools import tool


class WebSearch:
    """Utility for performing web searches and fetching web content.
    
    This class provides methods for searching the web using a search engine
    and fetching and parsing content from web pages.
    """
    
    def __init__(self, user_agent: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the web search utility.
        
        Args:
            user_agent: Optional custom user agent string
            api_key: Optional API key for search services (if applicable)
        """
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        self.api_key = api_key
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
    
    async def search_alternative(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Alternative search method using a different service if DuckDuckGo isn't working.
        
        Args:
            query: The search query
            num_results: Number of results to return (default: 5)
            
        Returns:
            List of search results with title, url, and snippet
        """
        # This is a fallback implementation using SerpAPI format
        # If you have a SerpAPI key, you can implement it here
        
        try:
            if not self.api_key:
                logger.warning("No API key provided for alternative search")
                return []
                
            # Sample implementation using a search API
            search_url = f"https://serpapi.com/search.json?q={query.replace(' ', '+')}&api_key={self.api_key}&num={num_results}"
            
            logger.info(f"Using alternative search for query: {query}")
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        logger.error(f"Alternative search failed with status code: {response.status}")
                        return []
                    
                    result_data = await response.json()
                    organic_results = result_data.get("organic_results", [])
                    
                    results = []
                    for result in organic_results[:num_results]:
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("link", ""),
                            "snippet": result.get("snippet", "")
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error during alternative search: {str(e)}")
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
            # Make sure URL is properly formatted
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
                
            logger.info(f"Fetching web page content: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    timeout=aiohttp.ClientTimeout(total=30)  # 30-second timeout
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
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching page content: {url}")
            return {
                "success": False,
                "url": url,
                "error": "Request timeout"
            }
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
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
                element.extract()
            
            # Remove hidden elements
            for element in soup.find_all(style=lambda value: value and ("display:none" in value or "display: none" in value)):
                element.extract()
            
            # Get text from main content areas if possible
            main_content = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup
            
            # Get text
            text = main_content.get_text(separator="\n")
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            # Remove empty lines and collapse whitespace
            cleaned_lines = []
            for line in lines:
                if line:
                    # Replace multiple spaces with single space
                    line = re.sub(r'\s+', ' ', line)
                    cleaned_lines.append(line)
            
            text = "\n".join(cleaned_lines)
            
            # Limit to a reasonable length (100KB)
            if len(text) > 100000:
                text = text[:100000] + "... [content truncated due to length]"
            
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
        
        if not search_results and self.api_key:
            logger.info("Primary search returned no results, trying alternative search")
            search_results = await self.search_alternative(query, num_results=num_results)
        
        # Fetch content for all results concurrently
        async def fetch_result(result):
            url = result.get("url")
            if not url:
                return None
            
            page_content = await self.fetch_page_content(url)
            if page_content.get("success"):
                return {
                    "title": result.get("title"),
                    "url": url,
                    "snippet": result.get("snippet"),
                    "content": page_content.get("text", "")
                }
            return None
        
        # Create tasks for all results
        tasks = [fetch_result(result) for result in search_results]
        fetched_contents = await asyncio.gather(*tasks)
        
        # Filter out None results
        fetched_results = [result for result in fetched_contents if result is not None]
        
        logger.info(f"Fetched content for {len(fetched_results)} search results")
        return fetched_results
    
    async def search_and_summarize(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """Search, fetch and create a summary of the results.
        
        Args:
            query: The search query
            num_results: Number of results to fetch content for (default: 3)
            
        Returns:
            Dictionary with the search results and a summary
        """
        results = await self.search_and_fetch(query, num_results=num_results)
        
        # Create a summary of the results
        summary = {
            "query": query,
            "num_results": len(results),
            "results": [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "snippet": result["snippet"],
                    # Truncate the content for the summary
                    "content_preview": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"]
                }
                for result in results
            ]
        }
        
        return {
            "summary": summary,
            "full_results": results
        }


class WebSearchTool(BaseTool):
    """Tool for performing web searches using the WebSearch utility."""
    
    name: str = "web_search"
    description: str = "Search the web for information on a specific topic"
    
    def __init__(self, web_search: Optional[WebSearch] = None):
        """Initialize the web search tool.
        
        Args:
            web_search: Optional WebSearch instance to use
        """
        super().__init__()
        self.web_search = web_search or WebSearch()
        
    async def _arun(self, query: str, num_results: int = 3, 
                   run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run the web search.
        
        Args:
            query: The search query
            num_results: Number of results to fetch (default: 3)
            run_manager: Optional callback manager
            
        Returns:
            JSON string with search results
        """
        if run_manager:
            await run_manager.on_text("Searching the web for: " + query)
            
        results = await self.web_search.search_and_fetch(query, num_results=num_results)
        
        # Format results as a JSON string
        return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def search_web(query: str, num_results: int = 3) -> str:
    """
    Search the web for information on a specific topic.
    
    Args:
        query: The search query
        num_results: Number of results to fetch (default: 3)
        
    Returns:
        JSON string with search results
    """
    # Create a synchronous wrapper for the async search function
    web_search = WebSearch()
    
    # Create an event loop and run the async function
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(web_search.search_and_fetch(query, num_results=num_results))
    
    return json.dumps(results, ensure_ascii=False, indent=2)