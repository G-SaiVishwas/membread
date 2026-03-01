"""
Membread Agent SDK Examples
=============================
Copy-paste examples for connecting AI agents to the Membread memory layer.
Supports: Python, LangGraph, CrewAI, AutoGen, LlamaIndex, and raw HTTP.
"""

# ─── Python SDK ───────────────────────────────────────────────────────────────

def python_basic():
    """Basic Python usage — store and recall agent memories."""
    from membread import Membread

    tg = Membread(api_key="YOUR_KEY", base_url="http://localhost:8000")

    # Store an agent observation with full lineage
    tg.store(
        observation="User prefers dark mode in VS Code and uses Fira Code font",
        agent_id="coding-agent-1",
        session_id="session-2024-01-15-a",
        task_id="editor-setup",
        metadata={"tool": "cursor", "confidence": 0.95},
    )

    # Cross-session recall — retrieves from ALL sessions for this agent
    ctx = tg.recall(
        query="What are the user's editor preferences?",
        agent_id="coding-agent-1",
        cross_session=True,
        max_tokens=2000,
    )
    print(ctx.context)
    print(f"Sources: {ctx.sources}")
    print(f"Continuity: {ctx.session_count} sessions, {ctx.tool_count} tools")


# ─── LangGraph Integration ───────────────────────────────────────────────────

def langgraph_example():
    """LangGraph — persistent agent memory across graph traversals."""
    from membread.integrations import MembreadMemory
    from langgraph.prebuilt import create_react_agent

    memory = MembreadMemory(
        api_key="YOUR_KEY",
        agent_id="langgraph-research",
        persist_sessions=True,
    )

    agent = create_react_agent(
        model,
        tools,
        checkpointer=memory,  # every step auto-persisted
    )

    # Memory carries across sessions automatically
    result = agent.invoke(
        {"messages": [("user", "Continue yesterday's research on transformer architectures")]},
        config={"configurable": {"thread_id": "research-alpha"}},
    )


# ─── CrewAI Integration ──────────────────────────────────────────────────────

def crewai_example():
    """CrewAI — shared memory across an agent crew."""
    from membread.integrations import MembreadCrewMemory
    from crewai import Agent, Crew

    memory = MembreadCrewMemory(
        api_key="YOUR_KEY",
        team_id="product-crew",
    )

    researcher = Agent(
        role="Researcher",
        memory=memory.for_agent("researcher"),
    )

    writer = Agent(
        role="Writer",
        memory=memory.for_agent("writer"),
        # Writer automatically sees Researcher's memories
    )

    crew = Crew(agents=[researcher, writer])
    result = crew.kickoff()


# ─── AutoGen Integration ─────────────────────────────────────────────────────

def autogen_example():
    """AutoGen — persistent assistant memory across conversations."""
    from membread.integrations import MembreadAutoGen
    import autogen

    memory = MembreadAutoGen(
        api_key="YOUR_KEY",
        agent_id="autogen-assistant",
    )

    assistant = autogen.AssistantAgent(
        "assistant",
        llm_config=llm_config,
        memory=memory,  # persistent across conversations
    )

    # Memory from previous chats is automatically loaded
    user_proxy.initiate_chat(
        assistant,
        message="Pick up where we left off on the API design",
    )


# ─── Raw HTTP ────────────────────────────────────────────────────────────────

def raw_http_example():
    """Raw HTTP — works with any language or tool."""
    import requests

    BASE = "http://localhost:8000"

    # 1. Get token
    token_resp = requests.post(f"{BASE}/api/auth/token", json={
        "tenant_id": "my-org",
        "user_id": "agent-user",
    })
    token = token_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Store agent memory
    requests.post(f"{BASE}/api/memory/store", json={
        "observation": "Deployment uses Kubernetes 1.28 with Istio service mesh",
        "metadata": {
            "agent_id": "devops-agent",
            "session_id": "deploy-session-42",
            "task_id": "infra-audit",
            "tool": "cursor",
        },
    }, headers=headers)

    # 3. Cross-session recall
    recall_resp = requests.post(f"{BASE}/api/memory/recall", json={
        "query": "What infrastructure is the project using?",
        "max_tokens": 2000,
    }, headers=headers)
    print(recall_resp.json()["context"])

    # 4. Temporal search — what did the agent know last week?
    temporal_resp = requests.post(f"{BASE}/api/memory/search/temporal", json={
        "query": "infrastructure setup",
        "as_of": "2024-01-08",
        "limit": 10,
    }, headers=headers)
    for hit in temporal_resp.json()["results"]:
        print(f"  [{hit['score']:.2f}] {hit['text'][:80]}")


if __name__ == "__main__":
    print("Membread Agent SDK Examples")
    print("Run individual functions to test each integration.")
