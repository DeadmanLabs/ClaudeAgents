import axios, { AxiosRequestConfig } from 'axios';
import { JSDOM } from 'jsdom';
import { logger } from './LoggerSetup';
import { 
  Tool,
  DynamicStructuredTool
} from 'langchain/tools';
import { z } from 'zod';
import { BaseCallbackConfig } from '@langchain/core/callbacks/manager';

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
 * Search and summarize result interface
 */
export interface SearchSummary {
  summary: {
    query: string;
    num_results: number;
    results: Array<{
      title: string;
      url: string;
      snippet: string;
      content_preview: string;
    }>;
  };
  full_results: SearchResult[];
}

/**
 * Utility for performing web searches and fetching web content.
 * Provides methods for searching the web using a search engine
 * and fetching and parsing content from web pages.
 */
export class WebSearch {
  private userAgent: string;
  private apiKey?: string;

  /**
   * Initialize the web search utility
   * 
   * @param userAgent - Optional custom user agent string
   * @param apiKey - Optional API key for search services (if applicable)
   */
  constructor(userAgent?: string, apiKey?: string) {
    this.userAgent = userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36';
    this.apiKey = apiKey;
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
        },
        timeout: 30000 // 30 second timeout
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
   * Alternative search method using a different service if DuckDuckGo isn't working
   * 
   * @param query - The search query
   * @param numResults - Number of results to return (default: 5)
   * @returns List of search results with title, url, and snippet
   */
  public async searchAlternative(query: string, numResults = 5): Promise<SearchResult[]> {
    // This is a fallback implementation using SerpAPI format
    // If you have a SerpAPI key, you can implement it here
    
    try {
      if (!this.apiKey) {
        logger.warning('No API key provided for alternative search');
        return [];
      }
      
      // Sample implementation using a search API
      const searchUrl = `https://serpapi.com/search.json?q=${query.replace(/ /g, '+')}&api_key=${this.apiKey}&num=${numResults}`;
      
      logger.info(`Using alternative search for query: ${query}`);
      const response = await axios.get(searchUrl);
      
      if (response.status !== 200) {
        logger.error(`Alternative search failed with status code: ${response.status}`);
        return [];
      }
      
      const resultData = response.data;
      const organicResults = resultData.organic_results || [];
      
      const results: SearchResult[] = [];
      for (let i = 0; i < Math.min(organicResults.length, numResults); i++) {
        const result = organicResults[i];
        results.push({
          title: result.title || '',
          url: result.link || '',
          snippet: result.snippet || ''
        });
      }
      
      return results;
    } catch (error) {
      logger.error(`Error during alternative search: ${error}`);
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
      // Make sure URL is properly formatted
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = `https://${url}`;
      }
      
      logger.info(`Fetching web page content: ${url}`);
      
      const options: AxiosRequestConfig = {
        headers: {
          'User-Agent': this.userAgent
        },
        timeout: 30000, // 30 seconds timeout
        maxContentLength: 10 * 1024 * 1024 // 10MB max content size
      };
      
      const response = await axios.get(url, options);
      
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
      const errorMsg = error instanceof Error ? error.message : String(error);
      logger.error(`Error fetching page content: ${errorMsg}`);
      
      // Check for timeout error
      if (errorMsg.includes('timeout')) {
        return {
          success: false,
          url,
          error: 'Request timeout'
        };
      }
      
      return {
        success: false,
        url,
        error: errorMsg
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
      
      // Remove unwanted elements
      const elementsToRemove = [
        'script', 'style', 'nav', 'footer', 'header', 
        'aside', 'noscript', 'iframe', 'ad', 'advertisement'
      ];
      
      elementsToRemove.forEach(tag => {
        const elements = document.querySelectorAll(tag);
        elements.forEach(element => element.remove());
      });
      
      // Remove hidden elements based on style attribute
      const allElements = document.querySelectorAll('*');
      allElements.forEach(element => {
        const style = element.getAttribute('style');
        if (style && (style.includes('display:none') || style.includes('display: none'))) {
          element.remove();
        }
      });
      
      // Get text from main content areas if possible
      let mainContent = document.querySelector('main') || 
                        document.querySelector('article') || 
                        document.querySelector('div[id="content"]') || 
                        document.body;
      
      // Get text content with newline separators
      let text = mainContent ? mainContent.textContent || '' : document.body.textContent || '';
      
      // Clean up text
      const lines = text.split('\n')
                        .map(line => line.trim())
                        .filter(line => line.length > 0);
      
      // Process each line to remove excessive whitespace
      const cleanedLines = lines.map(line => line.replace(/\s+/g, ' '));
      
      text = cleanedLines.join('\n');
      
      // Limit to a reasonable length (100KB)
      if (text.length > 100000) {
        text = text.substring(0, 100000) + '... [content truncated due to length]';
      }
      
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
    let searchResults = await this.search(query, numResults);
    
    if (searchResults.length === 0 && this.apiKey) {
      logger.info('Primary search returned no results, trying alternative search');
      searchResults = await this.searchAlternative(query, numResults);
    }
    
    // Fetch content for all results concurrently
    const fetchPromises = searchResults.map(async (result) => {
      if (!result.url) return null;
      
      try {
        const pageContent = await this.fetchPageContent(result.url);
        if (pageContent.success) {
          return {
            title: result.title,
            url: result.url,
            snippet: result.snippet,
            content: pageContent.text || ''
          };
        }
      } catch (error) {
        logger.error(`Error fetching content for ${result.url}: ${error}`);
      }
      
      return null;
    });
    
    // Wait for all fetches to complete
    const fetchedContents = await Promise.all(fetchPromises);
    
    // Filter out null results
    const fetchedResults = fetchedContents.filter((result): result is SearchResult => 
      result !== null
    );
    
    logger.info(`Fetched content for ${fetchedResults.length} search results`);
    return fetchedResults;
  }

  /**
   * Search, fetch and create a summary of the results
   * 
   * @param query - The search query
   * @param numResults - Number of results to fetch (default: 3)
   * @returns Dictionary with the search results and a summary
   */
  public async searchAndSummarize(query: string, numResults = 3): Promise<SearchSummary> {
    const results = await this.searchAndFetch(query, numResults);
    
    // Create a summary of the results
    const summary = {
      query,
      num_results: results.length,
      results: results.map(result => ({
        title: result.title,
        url: result.url,
        snippet: result.snippet,
        // Truncate the content for the summary
        content_preview: result.content && result.content.length > 500 ? 
          result.content.substring(0, 500) + '...' : 
          result.content || ''
      }))
    };
    
    return {
      summary,
      full_results: results
    };
  }
}

/**
 * LangChain tool for performing web searches
 */
export class WebSearchTool extends Tool {
  name = 'web_search';
  description = 'Search the web for information on a specific topic';
  private webSearch: WebSearch;
  
  constructor(webSearch?: WebSearch) {
    super();
    this.webSearch = webSearch || new WebSearch();
  }
  
  /** @ignore */
  async _call(query: string, runManager?: BaseCallbackConfig): Promise<string> {
    try {
      const results = await this.webSearch.searchAndFetch(query, 3);
      return JSON.stringify(results, null, 2);
    } catch (error) {
      throw new Error(`Error searching web: ${error}`);
    }
  }
}

/**
 * Create a structured web search tool with additional parameters
 * 
 * @returns A dynamic structured tool for web search
 */
export function createWebSearchTool(): DynamicStructuredTool<any, any> {
  const webSearch = new WebSearch();
  
  return new DynamicStructuredTool({
    name: 'web_search',
    description: 'Search the web for information on a specific topic',
    schema: z.object({
      query: z.string().describe('The search query'),
      numResults: z.number().optional().default(3).describe('Number of results to fetch')
    }),
    func: async ({ query, numResults = 3 }) => {
      try {
        const results = await webSearch.searchAndFetch(query, numResults);
        return JSON.stringify(results, null, 2);
      } catch (error) {
        throw new Error(`Error searching web: ${error}`);
      }
    }
  });
}