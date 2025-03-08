from typing import Any, Dict, List, Optional, AsyncGenerator, Union
import os
import aiohttp
import asyncio
from loguru import logger
import anthropic
import openai


class AIClient:
    """Client for AI services like Anthropic and OpenAI.
    
    This class provides a unified interface for working with different
    AI service providers, with support for streaming responses.
    """
    
    def __init__(self, provider: str = "anthropic"):
        """Initialize the AI client.
        
        Args:
            provider: The AI provider to use ('anthropic' or 'openai')
        """
        self.provider = provider.lower()
        
        # Initialize appropriate client based on provider
        if self.provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not found in environment variables")
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        elif self.provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            self.client = openai.AsyncOpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
        
        logger.info(f"Initialized AI client with provider: {self.provider}")
    
    async def generate(self, 
                     prompt: str, 
                     system_prompt: Optional[str] = None,
                     messages: Optional[List[Dict[str, str]]] = None,
                     temperature: float = 0.7,
                     max_tokens: int = 1000,
                     stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response from the AI model.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt to set context
            messages: Optional list of conversation messages (overrides prompt if provided)
            temperature: Controls randomness (0 to 1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Either the complete response text or an async generator that yields response chunks
        """
        if self.provider == "anthropic":
            return await self._generate_anthropic(prompt, system_prompt, messages, temperature, max_tokens, stream)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, system_prompt, messages, temperature, max_tokens, stream)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    async def _generate_anthropic(self, 
                               prompt: str, 
                               system_prompt: Optional[str],
                               messages: Optional[List[Dict[str, str]]],
                               temperature: float,
                               max_tokens: int,
                               stream: bool) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using Anthropic's Claude.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt to set context
            messages: Optional list of conversation messages (overrides prompt if provided)
            temperature: Controls randomness (0 to 1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Either the complete response text or an async generator that yields response chunks
        """
        # Prepare the messages
        if messages:
            formatted_messages = []
            for msg in messages:
                role = msg["role"]
                if role == "user":
                    formatted_messages.append({"role": "user", "content": msg["content"]})
                elif role == "assistant":
                    formatted_messages.append({"role": "assistant", "content": msg["content"]})
                elif role == "system":
                    # System message is handled separately in Anthropic
                    system_prompt = msg["content"]
        else:
            formatted_messages = [{"role": "user", "content": prompt}]
        
        try:
            if stream:
                # Streaming response
                with logger.contextualize(stream=True):
                    response = await self.client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_prompt,
                        messages=formatted_messages,
                        stream=True
                    )
                
                    async def response_generator():
                        async for chunk in response:
                            if chunk.delta.text:
                                yield chunk.delta.text
                    
                    return response_generator()
            else:
                # Non-streaming response
                response = await self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=formatted_messages
                )
                
                return response.content[0].text
                
        except Exception as e:
            logger.error(f"Error generating response from Anthropic: {str(e)}")
            raise
    
    async def _generate_openai(self, 
                            prompt: str, 
                            system_prompt: Optional[str],
                            messages: Optional[List[Dict[str, str]]],
                            temperature: float,
                            max_tokens: int,
                            stream: bool) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using OpenAI's models.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt to set context
            messages: Optional list of conversation messages (overrides prompt if provided)
            temperature: Controls randomness (0 to 1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Either the complete response text or an async generator that yields response chunks
        """
        # Prepare the messages
        if messages:
            formatted_messages = []
            for msg in messages:
                role = msg["role"]
                if role == "user":
                    formatted_messages.append({"role": "user", "content": msg["content"]})
                elif role == "assistant":
                    formatted_messages.append({"role": "assistant", "content": msg["content"]})
                elif role == "system":
                    formatted_messages.append({"role": "system", "content": msg["content"]})
        else:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            formatted_messages.append({"role": "user", "content": prompt})
        
        try:
            if stream:
                # Streaming response
                with logger.contextualize(stream=True):
                    response = await self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=formatted_messages,
                        stream=True
                    )
                
                    async def response_generator():
                        async for chunk in response:
                            if chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    
                    return response_generator()
            else:
                # Non-streaming response
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=formatted_messages
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {str(e)}")
            raise