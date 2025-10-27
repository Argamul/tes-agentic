import os
import asyncio
import json
import requests
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool, tool
from langchain.schema import HumanMessage
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Registry for managing and executing various tools that can be used by AI agents.
    Provides a collection of utility tools for different tasks.
    """
    
    def __init__(self):
        self.tools = []
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools with the registry."""
        self.tools = [
            CalculatorTool(),
            WeatherTool(),
            WebSearchTool(),
            FileReadTool(),
            TextAnalysisTool(),
            DateTimeTool(),
            MathTool(),
            TextProcessingTool()
        ]
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of available tools
        """
        return self.tools
    
    def list_tools(self) -> List[Dict[str, str]]:
        """
        Get list of available tools with descriptions.
        
        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a specific tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            tool = next((t for t in self.tools if t.name == tool_name), None)
            
            if not tool:
                raise Exception(f"Tool '{tool_name}' not found")
            
            # Execute tool
            result = await tool.arun(json.dumps(parameters))
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise Exception(f"Tool execution failed: {str(e)}")
    
    def add_tool(self, tool: BaseTool):
        """
        Add a new tool to the registry.
        
        Args:
            tool: Tool instance to add
        """
        self.tools.append(tool)
        logger.info(f"Added tool: {tool.name}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: Name of the tool to remove
            
        Returns:
            True if tool was removed, False if not found
        """
        for i, tool in enumerate(self.tools):
            if tool.name == tool_name:
                del self.tools[i]
                logger.info(f"Removed tool: {tool_name}")
                return True
        
        return False

# Tool Implementations

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Useful for performing mathematical calculations"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of calculator tool."""
        try:
            # Safe evaluation of mathematical expressions
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in query):
                return "Error: Invalid characters in expression"
            
            result = eval(query)
            return f"Result: {result}"
        except Exception as e:
            return f"Error calculating: {str(e)}"

class WeatherTool(BaseTool):
    name: str = "weather"
    description: str = "Get current weather information for a location"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of weather tool."""
        try:
            # This is a mock implementation
            # In a real application, you would integrate with a weather API
            return f"Weather information for {query}: 72°F, Sunny"
        except Exception as e:
            return f"Error getting weather: {str(e)}"

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of web search tool."""
        try:
            # This is a mock implementation
            # In a real application, you would integrate with a search API
            return f"Search results for '{query}': [Mock search results would appear here]"
        except Exception as e:
            return f"Error searching web: {str(e)}"

class FileReadTool(BaseTool):
    name: str = "file_read"
    description: str = "Read content from a file"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of file read tool."""
        try:
            params = json.loads(query)
            file_path = params.get("file_path", "")
            
            if not file_path:
                return "Error: file_path parameter is required"
            
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' not found"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"File content: {content[:1000]}..." if len(content) > 1000 else f"File content: {content}"
            
        except Exception as e:
            return f"Error reading file: {str(e)}"

class TextAnalysisTool(BaseTool):
    name: str = "text_analysis"
    description: str = "Analyze text for various metrics (word count, sentiment, etc.)"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of text analysis tool."""
        try:
            params = json.loads(query)
            text = params.get("text", "")
            
            if not text:
                return "Error: text parameter is required"
            
            # Basic text analysis
            word_count = len(text.split())
            char_count = len(text)
            sentence_count = len([s for s in text.split('.') if s.strip()])
            
            analysis = {
                "word_count": word_count,
                "character_count": char_count,
                "sentence_count": sentence_count,
                "average_words_per_sentence": round(word_count / sentence_count, 2) if sentence_count > 0 else 0
            }
            
            return f"Text analysis: {json.dumps(analysis, indent=2)}"
            
        except Exception as e:
            return f"Error analyzing text: {str(e)}"

class DateTimeTool(BaseTool):
    name: str = "datetime"
    description: str = "Get current date and time information"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of datetime tool."""
        try:
            now = datetime.now()
            
            time_info = {
                "current_date": now.strftime("%Y-%m-%d"),
                "current_time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "month": now.strftime("%B"),
                "year": now.year,
                "timestamp": now.timestamp()
            }
            
            return f"Current date/time: {json.dumps(time_info, indent=2)}"
            
        except Exception as e:
            return f"Error getting datetime: {str(e)}"

class MathTool(BaseTool):
    name: str = "math"
    description: str = "Perform mathematical operations and calculations"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of math tool."""
        try:
            params = json.loads(query)
            operation = params.get("operation", "")
            values = params.get("values", [])
            
            if not operation or not values:
                return "Error: operation and values parameters are required"
            
            if operation == "add":
                result = sum(values)
            elif operation == "multiply":
                result = math.prod(values)
            elif operation == "divide":
                if len(values) != 2:
                    return "Error: Division requires exactly 2 values"
                result = values[0] / values[1]
            elif operation == "power":
                if len(values) != 2:
                    return "Error: Power operation requires exactly 2 values"
                result = values[0] ** values[1]
            elif operation == "sqrt":
                if len(values) != 1:
                    return "Error: Square root requires exactly 1 value"
                result = math.sqrt(values[0])
            else:
                return f"Error: Unknown operation '{operation}'"
            
            return f"Result: {result}"
            
        except Exception as e:
            return f"Error in math operation: {str(e)}"

class TextProcessingTool(BaseTool):
    name: str = "text_processing"
    description: str = "Process and transform text (uppercase, lowercase, reverse, etc.)"
    
    async def _arun(self, query: str) -> str:
        """Async implementation of text processing tool."""
        try:
            params = json.loads(query)
            text = params.get("text", "")
            operation = params.get("operation", "")
            
            if not text or not operation:
                return "Error: text and operation parameters are required"
            
            if operation == "uppercase":
                result = text.upper()
            elif operation == "lowercase":
                result = text.lower()
            elif operation == "reverse":
                result = text[::-1]
            elif operation == "title_case":
                result = text.title()
            elif operation == "remove_spaces":
                result = text.replace(" ", "")
            elif operation == "count_words":
                result = str(len(text.split()))
            elif operation == "count_chars":
                result = str(len(text))
            else:
                return f"Error: Unknown operation '{operation}'"
            
            return f"Processed text: {result}"
            
        except Exception as e:
            return f"Error processing text: {str(e)}"



