_CLAUDE_PYTHON_SAMPLE = """
```python
from jentic import Jentic
import anthropic
import os


class JenticAgent:
    def __init__(self):
        # Initialize your project with your Anthropic API Key
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation_history = []

        self.jentic = Jentic()
        self.jentic_tools = self.jentic.generate_llm_tool_definitions("anthropic")

    async def process_message(self, user_message): 
        # Add the user message
        messages = self.conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Get initial response
        response = self.client.messages.create(
            model='claude-3-5-sonnet-latest',  
            messages=messages,
            tools=self.jentic_tools,
            max_tokens=1024
        )
        
        while response.stop_reason == "tool_use":
            tool_use = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use.name
            tool_input = tool_use.input
            
            # Add the assistant's response with the tool use to the conversation
            messages.append({
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me search for that information."},
                    {"type": "tool_use", "id": tool_use.id, "name": tool_name, "input": tool_input}
                ]
            })
            
            try:
                # Execute the tool
                tool_result = await self.jentic.run_llm_tool(
                    tool_name,
                    tool_input 
                )
                
                # Add tool result to conversation
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": str(tool_result)
                        }
                    ]
                })
            except Exception as e:
                error_message = f"Error executing tool {tool_name}: {str(e)}"
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"Error: {error_message}"
                        }
                    ]
                })
            
            # Get follow-up response
            response = self.client.messages.create(
                model='claude-3-5-sonnet-latest',  
                messages=messages,
                tools=self.jentic_tools,
                max_tokens=1024
            )
        
        # Save the conversation history for context
        self.conversation_history = messages + [{
            "role": "assistant",
            "content": response.content
        }]
        
        # Keep conversation history manageable (last 10 messages)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        # Return the final text response
        return response.content[0].text
```
"""

_CHATGPT_PYTHON_SAMPLE = """
```python
from jentic import Jentic
import openai
import os

class JenticAgent:
    def __init__(self):
        # Initialize your project with your OpenAI API Key
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        
        self.jentic = Jentic()
        self.jentic_tools = self.jentic.generate_llm_tool_definitions("openai")
        
    async def process_message(self, user_message):
        # Add the user message to history
        messages = self.conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Get response from OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            tools=self.jentic_tools,
            max_tokens=1024
        )
        
        # Process the response
        assistant_message = response.choices[0].message
        
        # Check if the model wants to use a tool
        while assistant_message.tool_calls:
            # Add the assistant's response to conversation history
            messages.append(assistant_message)
            
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = tool_call.function.arguments
                
                try:
                    # Execute the tool
                    tool_result = await self.jentic.run_llm_tool(
                        tool_name,
                        tool_input
                    )
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })
                    
                except Exception as e:
                    error_message = f"Error executing tool {tool_name}: {str(e)}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {error_message}"
                    })
            
            # Get follow-up response
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                tools=self.jentic_tools,
                max_tokens=1024
            )
            assistant_message = response.choices[0].message
        
        # Add final response to conversation history
        messages.append(assistant_message)
        
        # Update conversation history
        self.conversation_history = messages
        
        # Keep conversation history manageable (last 10 messages)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        # Return the final text response
        return assistant_message.content
```
"""

# Public dictionary mapping formats to language-specific code samples
CODE_SAMPLES = {
    "claude": {"python": _CLAUDE_PYTHON_SAMPLE},
    "chatgpt": {"python": _CHATGPT_PYTHON_SAMPLE},
}
