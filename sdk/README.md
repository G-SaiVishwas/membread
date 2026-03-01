# Membread SDK

Persistent memory layer for AI agents. One central knowledge base accessible from every tool.

## Install

```bash
# From the repo root
pip install -e ./sdk
```

With integrations:
```bash
pip install -e "./sdk[langchain]"   # LangChain / LangGraph
pip install -e "./sdk[crewai]"      # CrewAI
pip install -e "./sdk[autogen]"     # Microsoft AutoGen
pip install -e "./sdk[openai]"      # OpenAI monkey-patch
pip install -e "./sdk[all]"         # Everything
```

## Quick Start

```python
from membread import MembreadClient

client = MembreadClient(
    api_url="http://localhost:8000",
    token="your-jwt-token",
)

# Store a memory
client.store("User prefers dark mode", source="my-agent", session_id="sess-1")

# Recall relevant context
result = client.recall("What are the user preferences?")
print(result["context"])
```

## LangChain Integration

```python
from membread.integrations.langchain import MembreadLangChainMemory
from langchain.chains import ConversationChain

memory = MembreadLangChainMemory(token="eyJ...")
chain = ConversationChain(llm=llm, memory=memory)
chain.run("What do you know about the user?")
```

## CrewAI Integration

```python
from membread.integrations.crewai import MembreadCrewAITool

tool = MembreadCrewAITool(token="eyJ...")
agent = Agent(role="Researcher", tools=[tool])
```

## OpenAI Auto-Capture

```python
from membread import patch_openai

patch_openai(token="eyJ...")

# All OpenAI calls are now automatically stored
import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## AutoGen Integration

```python
from membread.integrations.autogen import MembreadAutoGenMemory

memory = MembreadAutoGenMemory(token="eyJ...")
memory.attach(assistant_agent)
# All messages are now captured
```
