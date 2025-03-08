import axios from 'axios';
import { JSDOM } from 'jsdom';
import { logger } from './LoggerSetup';

/**
 * Search result interface
 */
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  content?: string;
}

/**
 * Page content fetch result
 */
export interface PageContent {
  success: boolean;
  url: string;
  statusCode?: number;
  html?: string;
  text?: string;
  error?: string;
}

/**
 * Utility for performing web searches and fetching web content.
 * Provides methods for searching the web using a search engine
 * and fetching and parsing content from web pages.
 */
export class WebSearch {
  private userAgent: string;

  /**
   * Initialize the web search utility
   * 
   * @param userAgent - Optional custom user agent string
   */
  constructor(userAgent?: string) {
    this.userAgent = userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36';
    logger.debug(`WebSearch initialized with user agent: ${this.userAgent}`);
  }

  /**
   * Search the web using DuckDuckGo
   * 
   * @param query - The search query
   * @param numResults - Number of results to return (default: 5)
   * @param searchRegion - Region code for search results (default: wt-wt for worldwide)
   * @returns List of search results with title, url, and snippet
   */
  public async search(query: string, numResults = 5, searchRegion = 'wt-wt'): Promise<SearchResult[]> {
    try {
      // Use DuckDuckGo search
      const encodedQuery = query.replace(/ /g, '+');
      const searchUrl = `https://html.duckduckgo.com/html/?q=${encodedQuery}&kl=${searchRegion}`;
      
      logger.info(`Searching web for query: ${query}`);
      
      const response = await axios.get(searchUrl, {
        headers: {
          'User-Agent': this.userAgent
        }
      });
      
      if (response.status !== 200) {
        logger.error(`Search request failed with status code: ${response.status}`);
        return [];
      }
      
      const htmlContent = response.data;
      const dom = new JSDOM(htmlContent);
      const document = dom.window.document;
      
      const results: SearchResult[] = [];
      const resultElements = document.querySelectorAll('.result');
      
      for (let i = 0; i < Math.min(resultElements.length, numResults); i++) {
        const result = resultElements[i];
        const titleElem = result.querySelector('.result__title');
        const urlElem = result.querySelector('.result__url');
        const snippetElem = result.querySelector('.result__snippet');
        
        if (titleElem && urlElem) {
          const title = titleElem.textContent?.trim() || '';
          const url = urlElem.textContent?.trim() || '';
          const snippet = snippetElem?.textContent?.trim() || '';
          
          results.push({
            title,
            url,
            snippet
          });
        }
      }
      
      logger.info(`Found ${results.length} search results`);
      return results;
    } catch (error) {
      logger.error(`Error during web search: ${error}`);
      return [];
    }
  }

  /**
   * Fetch content from a web page
   * 
   * @param url - URL of the web page to fetch
   * @param extractText - Whether to extract readable text from the page (default: true)
   * @returns Dictionary containing page details and content
   */
  public async fetchPageContent(url: string, extractText = true): Promise<PageContent> {
    try {
      logger.info(`Fetching web page content: ${url}`);
      
      const response = await axios.get(url, {
        headers: {
          'User-Agent': this.userAgent
        }
      });
      
      if (response.status !== 200) {
        logger.error(`Page fetch failed with status code: ${response.status}`);
        return {
          success: false,
          url,
          statusCode: response.status,
          error: `HTTP status ${response.status}`
        };
      }
      
      const contentType = response.headers['content-type']?.toLowerCase() || '';
      if (!contentType.startsWith('text/html')) {
        logger.warning(`Non-HTML content type: ${contentType}`);
        return {
          success: false,
          url,
          statusCode: response.status,
          error: `Unsupported content type: ${contentType}`
        };
      }
      
      const htmlContent = response.data;
      
      const result: PageContent = {
        success: true,
        url,
        statusCode: response.status,
        html: htmlContent
      };
      
      if (extractText) {
        const textContent = this.extractTextFromHtml(htmlContent);
        result.text = textContent;
      }
      
      return result;
    } catch (error) {
      logger.error(`Error fetching page content: ${error}`);
      return {
        success: false,
        url,
        error: String(error)
      };
    }
  }

  /**
   * Extract readable text from HTML content
   * 
   * @param htmlContent - HTML content to extract text from
   * @returns Extracted text content
   */
  private extractTextFromHtml(htmlContent: string): string {
    try {
      const dom = new JSDOM(htmlContent);
      const document = dom.window.document;
      
      // Remove script and style elements
      const elementsToRemove = ['script', 'style', 'nav', 'footer', 'header'];
      elementsToRemove.forEach(tag => {
        const elements = document.querySelectorAll(tag);
        elements.forEach(element => element.remove());
      });
      
      // Get text content
      let text = document.body.textContent || '';
      
      // Clean up text
      text = text
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .join('\n');
      
      // Collapse multiple spaces
      text = text.replace(/\s+/g, ' ');
      
      return text;
    } catch (error) {
      logger.error(`Error extracting text from HTML: ${error}`);
      return '';
    }
  }

  /**
   * Search and fetch content from top results in one operation
   * 
   * @param query - The search query
   * @param numResults - Number of results to fetch content for (default: 3)
   * @returns List of search results with fetched content
   */
  public async searchAndFetch(query: string, numResults = 3): Promise<SearchResult[]> {
    const searchResults = await this.search(query, numResults);
    
    const fetchedResults: SearchResult[] = [];
    
    for (const result of searchResults) {
      if (result.url) {
        const pageContent = await this.fetchPageContent(result.url);
        if (pageContent.success) {
          fetchedResults.push({
            title: result.title,
            url: result.url,
            snippet: result.snippet,
            content: pageContent.text || ''
          });
        }
      }
    }
    
    logger.info(`Fetched content for ${fetchedResults.length} search results`);
    return fetchedResults;
  }
}