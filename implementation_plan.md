# Ask-the-Web Agent — Complete Architecture & Implementation Plan

> **A Senior AI Engineer's Blueprint for Building a Production-Grade Perplexity-like Search Agent**

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ASK-THE-WEB: Agentic AI Search Engine                                       ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║  • Multi-step reasoning with ReACT + ReWOO                                   ║
║  • Real-time web search with citation tracking                               ║
║  • Streaming responses with source cards                                     ║
║  • NVIDIA NIM + GitHub Models integration                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 1. Educational Guide & Senior Concepts

> **Why this architecture?** This section breaks down the advanced concepts used in this project, explaining the *what*, *why*, and *how* for each pattern.

### 1.1 Dual-Provider LLM Strategy
**Concept**: Abstraction layer that routes requests between primary (NVIDIA NIM) and fallback (GitHub Models) providers.
- **Why**: Reliance on a single provider creates a single point of failure and vendor lock-in. NVIDIA NIM offers specialized models (Nemotron) for tool calling, while GitHub Models provides access to GPT-5/o1 for reasoning fallbacks.
- **Implementation**: `UnifiedLLMClient` class catches distinct provider errors and seamlessly retries with the alternative, transparent to the agent logic.

### 1.2 Agentic Patterns

#### A. ReACT (Reasoning + Acting)
**Concept**: A loop where the model "thinks" (Reason), decides to use a tool (Act), and reads the output (Observation).
- **Why**: Standard LLMs can't interact with the world. ReACT allows them to use tools step-by-step.
- **Flow**: `Query` → `Thought: I need to search X` → `Action: WebSearch(X)` → `Observation: Results...` → `Thought: I have the answer` → `Final Answer`.

#### B. ReWOO (Reasoning WithOut Observation)
**Concept**: The agent plans *all* steps upfront before executing any tools.
- **Why**: ReACT is serial (slow). ReWOO allows parallel execution of independent steps (e.g., searching for "Tesla stock" and "Rivian stock" simultaneously).
- **Flow**: `Query` → `Plan: 1. Search X, 2. Search Y` → `Execute 1 & 2 (Parallel)` → `Synthesize`.

#### C. Reflexion
**Concept**: A feedback loop where the agent critiques its own output.
- **Why**: LLMs can hallucinate. Reflexion forces a "self-correction" pass before showing the user the answer.
- **Flow**: `Draft Answer` → `Critique: "Did I cite sources?"` → `Correction` → `Final Answer`.

#### D. Tree Search
**Concept**: Exploring multiple reasoning paths for complex problems, similar to chess engines.
- **Why**: Linear thinking often gets stuck. Tree Search explores "Branch A" and "Branch B", evaluates which looks more promising, and prunes bad paths.
- **Implementation**: Generate 3 distinct plans, score them, execute the best one.

### 1.3 Multi-Agent Orchestration
**Concept**: Specialized agents (workers) managed by a central supervisor (orchestrator).
- **Why**: A single prompt trying to do research, writing, and coding gets confused. Specialization improves performance.
- **Roles**:
  - **Orchestrator**: Breaks down the query ("Research X", then "Write Y").
  - **Researcher**: Optimized for search queries and reading execution.
  - **writer**: Optimized for clear, cited prose.
  - **Critic**: Optimized for fact-checking.

### 1.4 Advanced RAG (Retrieval-Augmented Generation)
**Concept**: Enhancing the LLM's context with retrieved data using high-quality embeddings.
- **Why**: Keyword search is brittle. Semantic search (embeddings) finds meaning.
- **Tech**: **NeMo Retriever** creates vector embeddings of documents. **NeMo Reranker** re-orders results so the LLM sees the *most* relevant text first, reducing "lost in the middle" phenomena.

### 1.5 Real-Time Streaming (SSE)
**Concept**: Pushing data to the browser as it generates, rather than waiting for the full response.
- **Why**: Users hate waiting 10 seconds for an answer. Streaming shows "Thinking...", "Searching...", and tokens immediately.
- **Tech**: Server-Sent Events (SSE) keep a persistent connection open to push updates.

---

## 2. System Architecture Overview

```mermaid
flowchart TB
    subgraph UserLayer["🖥️ Presentation Layer"]
        UI[Next.js 14 Web App]
        SSE[SSE Stream Handler]
    end

    subgraph Gateway["🔒 API Gateway"]
        FastAPI[FastAPI Server]
        RateLimit[Rate Limiter]
        Auth[Auth Middleware]
    end

    subgraph AgentLayer["🧠 Agentic Core"]
        Router[Query Router]
        
        subgraph Orchestrator["Orchestrator"]
            Planner[ReWOO Planner]
            ReACT[ReACT Executor]
            Reflect[Reflexion Module]
            TreeSearch[Tree Search<br/>Complex Queries]
        end
        
        subgraph Workers["Worker Agents"]
            Researcher[Research Agent]
            Synthesizer[Synthesis Agent]
            Critic[Critic Agent]
        end
    end

    subgraph ToolLayer["🔧 Tool System"]
        Registry[Tool Registry]
        WebSearch[🔍 Web Search<br/>Tavily API]
        Scraper[📄 Web Scraper<br/>Playwright]
        Calculator[🧮 Calculator]
        CodeExec[💻 Code Executor<br/>Sandboxed]
    end

    subgraph LLMLayer["🤖 Model Providers"]
        subgraph NVIDIA["NVIDIA NIM"]
            Nemotron[Nemotron-3-Nano-30B<br/>Tool Calling + Reasoning]
            NemoEmbed[NeMo Retriever<br/>Embeddings]
            NemoRerank[NeMo Reranker]
        end
        
        subgraph GitHub["GitHub Models"]
            GPT5[GPT-5 / o3-mini<br/>Fallback LLM]
            Phi4[Phi-4-reasoning<br/>Fast Inference]
            TextEmbed[text-embedding-3-large]
        end
    end

    subgraph DataLayer["💾 Data Layer"]
        Redis[(Redis<br/>Cache + Sessions)]
        Postgres[(PostgreSQL<br/>History + Analytics)]
        VectorDB[(pgvector<br/>Semantic Search)]
    end

    UI --> SSE --> FastAPI
    FastAPI --> RateLimit --> Auth --> Router
    Router --> Planner
    Planner --> ReACT
    ReACT --> Registry
    Registry --> WebSearch & Scraper & Calculator & CodeExec
    ReACT --> Reflect
    Reflect --> TreeSearch
    
    Orchestrator --> Workers
    Workers --> LLMLayer
    
    AgentLayer --> NVIDIA
    AgentLayer --> GitHub
    
    ToolLayer --> DataLayer
    AgentLayer --> DataLayer
```

---

## 3. Agentic Patterns Deep Dive

### 3.1 Agency Levels

```mermaid
graph LR
    subgraph L1["Level 1: Simple"]
        A1[Direct LLM Call]
    end
    
    subgraph L2["Level 2: Workflow"]
        A2[Prompt Chaining] --> B2[Routing]
    end
    
    subgraph L3["Level 3: Agentic"]
        A3[ReACT Loop] --> B3[Tool Calling]
    end
    
    subgraph L4["Level 4: Multi-Agent"]
        A4[Orchestrator] --> B4[Worker Agents]
    end
    
    L1 --> L2 --> L3 --> L4
    
    style L3 fill:#10b981,color:#fff
    style L4 fill:#8b5cf6,color:#fff
```

### 3.2 Query Router Architecture

```python
# Classifies query complexity → selects optimal execution path
class QueryRouter:
    """
    Routes queries based on complexity analysis:
    - SIMPLE: Direct LLM response (no tools)
    - SEARCH: Single web search + synthesis
    - RESEARCH: Multi-step ReACT with tools
    - ANALYSIS: Tree search for complex reasoning
    """
```

| Query Type | Example | Execution Path |
|------------|---------|----------------|
| **SIMPLE** | "What is Python?" | Direct LLM → Response |
| **SEARCH** | "Latest news on AI" | WebSearch → Synthesize |
| **RESEARCH** | "Compare Tesla vs Rivian sales" | ReACT Loop (3-5 steps) |
| **ANALYSIS** | "Best investment strategy for 2026" | Tree Search + Multi-Agent |

### 3.3 ReACT Implementation

```mermaid
sequenceDiagram
    participant U as User
    participant R as ReACT Agent
    participant T as Tools
    participant L as LLM
    
    U->>R: Query
    
    loop Max 5 Iterations
        R->>L: Generate Thought
        L-->>R: Thought: I need to search for X
        
        R->>L: Select Action
        L-->>R: Action: web_search(query="X")
        
        R->>T: Execute Tool
        T-->>R: Observation: [Results]
        
        alt Has Enough Info
            R->>L: Generate Final Answer
            L-->>R: Answer with Citations
        end
    end
    
    R->>U: Streamed Response
```

### 3.4 ReWOO (Plan-then-Execute)

```mermaid
graph TD
    Q[Query] --> P[Planner LLM]
    
    P --> |"Plan"| S1["Step 1: Search 'topic A'"]
    P --> S2["Step 2: Search 'topic B'"]
    P --> S3["Step 3: Scrape URL"]
    P --> S4["Step 4: Synthesize all"]
    
    S1 --> |Parallel| E[Executor]
    S2 --> |Parallel| E
    S3 --> |Wait for S1/S2| E
    S4 --> |Wait for S3| E
    
    E --> R[Final Response]
    
    style P fill:#3b82f6,color:#fff
    style E fill:#10b981,color:#fff
```

### 3.5 Reflexion Pattern

```python
class ReflexionAgent:
    """
    Self-improving agent that:
    1. Generates initial response
    2. Critiques own response (hallucination check)
    3. Identifies improvement areas
    4. Regenerates with corrections
    """
    
    async def run(self, query: str) -> Response:
        # Initial generation
        response = await self.generate(query)
        
        # Self-critique
        critique = await self.evaluate(response)
        
        if critique.needs_improvement:
            # Regenerate with feedback
            response = await self.regenerate(query, critique)
        
        return response
```

### 3.6 Tree Search for Complex Queries

```mermaid
graph TD
    Q[Complex Query] --> N1[Option A]
    Q --> N2[Option B]
    Q --> N3[Option C]
    
    N1 --> N1A[Sub-search 1]
    N1 --> N1B[Sub-search 2]
    
    N2 --> N2A[Sub-search 1]
    N2 --> N2B[Sub-search 2]
    
    N1A --> |Score: 0.8| E1[Evaluate]
    N1B --> |Score: 0.6| E1
    N2A --> |Score: 0.9| E2[Evaluate]
    N2B --> |Score: 0.7| E2
    
    E1 --> |Prune low scores| BEST[Best Path]
    E2 --> BEST
    
    BEST --> FINAL[Final Synthesis]
    
    style N2A fill:#10b981,color:#fff
    style BEST fill:#8b5cf6,color:#fff
```

---

## 4. Multi-Agent System

### 4.1 Orchestrator-Worker Pattern

```mermaid
graph TB
    subgraph Orchestrator["🎭 Orchestrator Agent"]
        O[Task Decomposition<br/>+ Coordination]
    end
    
    subgraph Workers["👷 Specialized Workers"]
        W1[Research Agent<br/>Web Search + Scraping]
        W2[Analysis Agent<br/>Data Processing]
        W3[Writing Agent<br/>Response Synthesis]
        W4[Critic Agent<br/>Quality Assurance]
    end
    
    subgraph Messages["📨 Message Queue"]
        MQ[Redis Pub/Sub]
    end
    
    O --> |Delegate Tasks| MQ
    MQ --> W1 & W2 & W3 & W4
    W1 & W2 & W3 --> |Results| MQ
    W4 --> |Feedback| MQ
    MQ --> |Aggregate| O
```

### 4.2 Agent Communication Protocol

```python
@dataclass
class AgentMessage:
    sender: str          # "orchestrator" | "researcher" | "critic"
    recipient: str       # Target agent ID
    action: str          # "TASK" | "RESULT" | "FEEDBACK"
    payload: dict        # Task details or results
    correlation_id: str  # Track conversation thread
```

---

## 5. Tool System Design

### 5.1 Tool Registry

```python
class ToolRegistry:
    """Central registry for all available tools"""
    
    tools: Dict[str, BaseTool] = {
        "web_search": WebSearchTool(),
        "web_scraper": WebScraperTool(),
        "calculator": CalculatorTool(),
        "code_executor": CodeExecutorTool(),
    }
    
    def get_openai_tools(self) -> List[dict]:
        """Export tools in OpenAI function calling format"""
        return [tool.to_openai_schema() for tool in self.tools.values()]
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute tool with timeout and error handling"""
        tool = self.tools[name]
        return await asyncio.wait_for(
            tool.execute(**kwargs),
            timeout=30.0
        )
```

### 5.2 Tool Schemas

```python
# Web Search Tool
{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information on any topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return"
                }
            },
            "required": ["query"]
        }
    }
}
```

### 5.3 Tool Execution Flow

```mermaid
sequenceDiagram
    participant A as Agent
    participant R as Registry
    participant T as Tool
    participant E as External API
    
    A->>R: execute("web_search", query="...")
    R->>R: Validate parameters
    R->>T: WebSearchTool.execute()
    T->>E: Tavily API call
    E-->>T: Raw results
    T->>T: Parse + format
    T-->>R: ToolResult(success, data)
    R-->>A: Formatted observation
```

---

## 6. Model Provider Abstraction

### 6.1 Unified LLM Client

```python
class UnifiedLLMClient:
    """
    Abstraction layer supporting multiple providers:
    - NVIDIA NIM (primary)
    - GitHub Models (fallback)
    """
    
    providers = {
        "nvidia": {
            "reasoning": "nvidia/nemotron-3-nano-30b-a3b",
            "embedding": "nvidia/llama-3_2-nemoretriever-300m-embed-v2",
            "rerank": "nvidia/nv-rerankqa-mistral-4b-v3",
        },
        "github": {
            "reasoning": "azure-openai/gpt-5",
            "fast": "azureml/Phi-4-reasoning",
            "embedding": "azure-openai/text-embedding-3-large",
        }
    }
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """Unified chat interface with automatic fallback"""
        try:
            async for chunk in self._nvidia_chat(messages, tools, stream):
                yield chunk
        except ProviderError:
            async for chunk in self._github_chat(messages, tools, stream):
                yield chunk
```

### 6.2 Model Selection Matrix

| Use Case | Primary (NVIDIA) | Fallback (GitHub) |
|----------|------------------|-------------------|
| **Reasoning + Tool Calling** | Nemotron-3-Nano-30B | GPT-5 / o3-mini |
| **Fast Classification** | Nemotron (cached) | Phi-4-reasoning |
| **Embeddings** | NeMo Retriever 300M | text-embedding-3-large |
| **Reranking** | NeMo Reranker | Cohere Rerank |

---

## 7. Project Structure

```
ask-the-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # Pydantic Settings
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── chat.py            # POST /chat, GET /stream
│   │   │   │   ├── history.py         # Conversation history
│   │   │   │   └── health.py
│   │   │   └── middleware/
│   │   │       ├── rate_limit.py
│   │   │       └── cors.py
│   │   │
│   │   ├── agent/
│   │   │   ├── core.py                # Main orchestrator
│   │   │   ├── router.py              # Query classification
│   │   │   ├── react.py               # ReACT loop
│   │   │   ├── rewoo.py               # Plan-then-execute
│   │   │   ├── reflection.py          # Self-correction
│   │   │   ├── tree_search.py         # Complex reasoning
│   │   │   └── multi_agent/
│   │   │       ├── orchestrator.py
│   │   │       ├── researcher.py
│   │   │       ├── synthesizer.py
│   │   │       └── critic.py
│   │   │
│   │   ├── tools/
│   │   │   ├── base.py                # BaseTool ABC
│   │   │   ├── registry.py
│   │   │   ├── web_search.py          # Tavily integration
│   │   │   ├── web_scraper.py         # Playwright
│   │   │   ├── calculator.py
│   │   │   └── code_executor.py       # Sandboxed execution
│   │   │
│   │   ├── llm/
│   │   │   ├── client.py              # Unified LLM client
│   │   │   ├── nvidia.py              # NVIDIA NIM
│   │   │   ├── github.py              # GitHub Models
│   │   │   ├── prompts.py             # System prompts
│   │   │   └── streaming.py           # SSE handlers
│   │   │
│   │   ├── models/
│   │   │   ├── request.py             # API request schemas
│   │   │   ├── response.py            # API response schemas
│   │   │   └── agent.py               # Internal agent types
│   │   │
│   │   └── utils/
│   │       ├── citations.py           # Citation extraction
│   │       └── markdown.py            # Response formatting
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   │
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── SourceCard.tsx
│   │   │   ├── StreamingText.tsx
│   │   │   ├── SearchInput.tsx
│   │   │   ├── AgentThinking.tsx      # Shows agent's thought process
│   │   │   └── CitationPopover.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   └── useStreaming.ts
│   │   │
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts
│   │
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 8. API Design

### 8.1 Chat Endpoint

```yaml
POST /api/v1/chat
Content-Type: application/json

Request:
{
  "query": "Compare the AI strategies of NVIDIA and Google in 2026",
  "conversation_id": "uuid-optional",
  "settings": {
    "model": "nemotron-3-nano-30b",
    "search_depth": "deep",        # "quick" | "normal" | "deep"
    "max_sources": 10,
    "enable_reflection": true
  }
}

Response:
{
  "job_id": "job-uuid",
  "stream_url": "/api/v1/chat/stream/job-uuid"
}
```

### 8.2 Streaming Events

```typescript
// SSE Event Types
interface StreamEvent {
  type: "thinking" | "tool_call" | "tool_result" | "content" | "sources" | "done";
  data: ThinkingData | ToolCallData | ContentData | SourcesData;
}

// Example stream:
data: {"type": "thinking", "data": {"thought": "I need to search for NVIDIA AI strategy..."}}
data: {"type": "tool_call", "data": {"tool": "web_search", "args": {"query": "NVIDIA AI strategy 2026"}}}
data: {"type": "tool_result", "data": {"sources": [...]}}
data: {"type": "content", "data": {"delta": "NVIDIA has been focusing on..."}}
data: {"type": "sources", "data": {"citations": [{"id": 1, "url": "...", "title": "..."}]}}
data: {"type": "done", "data": {"total_tokens": 1500, "duration_ms": 3200}}
```

---

## 9. Frontend Components

### 9.1 Chat Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Ask-the-Web                                    [Dark Mode]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ USER: Compare Tesla and Rivian EV sales in 2025         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🤔 Thinking...                                           │   │
│  │ ├─ Searching: "Tesla EV sales 2025"                     │   │
│  │ ├─ Searching: "Rivian deliveries 2025"                  │   │
│  │ └─ Synthesizing results...                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Based on recent data, here's the comparison:            │   │
│  │                                                          │   │
│  │ **Tesla** delivered approximately 1.8M vehicles [1]     │   │
│  │ while **Rivian** reached 100K deliveries [2]...         │   │
│  │                                                          │   │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐                 │   │
│  │ │ 📰 [1]    │ │ 📰 [2]    │ │ 📰 [3]    │                 │   │
│  │ │ Reuters  │ │ Rivian IR │ │ Electrek │                 │   │
│  │ └──────────┘ └──────────┘ └──────────┘                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 💬 Ask a follow-up...                            [Send] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Suggested: "What about profit margins?" | "Market share?"     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Environment Configuration

```env
# ═══════════════════════════════════════════════════════════════
# MODEL PROVIDERS
# ═══════════════════════════════════════════════════════════════

# NVIDIA NIM (Primary)
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1

# GitHub Models (Fallback)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_MODELS_BASE=https://models.inference.ai.azure.com

# ═══════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════

# Web Search (Tavily - optimized for AI)
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ═══════════════════════════════════════════════════════════════
# INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════

# Redis (caching, rate limiting)
REDIS_URL=redis://localhost:6379/0

# PostgreSQL (history, analytics)
DATABASE_URL=postgresql://user:pass@localhost:5432/askweb

# ═══════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════

ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
MAX_CONCURRENT_REQUESTS=100
```

---

## 11. Verification Plan

### 11.1 Automated Tests

| Test Suite | Command | Coverage |
|------------|---------|----------|
| Unit Tests | `pytest tests/unit/ -v` | Tools, Router, Agent logic |
| Integration | `pytest tests/integration/ -v` | API endpoints, LLM calls |
| E2E | `npm run test:e2e` | Full user flows |

### 11.2 Manual Test Cases

1. **Simple Query**: "What is the capital of France?"
   - Expect: Direct response, no tool calls

2. **Search Query**: "Latest NVIDIA stock price"
   - Expect: Web search → Response with source

3. **Research Query**: "Compare GPT-5 vs Claude 4 capabilities"
   - Expect: Multiple searches → Synthesis → Citations

4. **Complex Analysis**: "Best AI investment strategy for 2026"
   - Expect: Tree search → Multi-agent → Detailed report

---

## 12. Resume Highlights

| Feature | Technical Depth | Impact |
|---------|-----------------|--------|
| **Multi-Provider LLM** | NVIDIA NIM + GitHub Models abstraction | Cost optimization, reliability |
| **Agentic Patterns** | ReACT, ReWOO, Reflexion, Tree Search | State-of-the-art reasoning |
| **Multi-Agent System** | Orchestrator-Worker with message queue | Scalable architecture |
| **Real-Time Streaming** | SSE with thought process visibility | Premium UX |
| **Tool Calling** | OpenAI-compatible with parallel execution | Extensible |
| **Production Ready** | Docker, Redis, PostgreSQL, rate limiting | Enterprise-grade |

---

## 13. Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| **1** | Core Setup | Project structure, LLM clients, basic API |
| **2** | Tool System | Web search, scraper, registry, execution |
| **3** | Agent Core | ReACT loop, router, basic orchestration |
| **4** | Advanced Agents | ReWOO, Reflexion, multi-agent |
| **5** | Frontend | Next.js UI, streaming, source cards |
| **6** | Polish | Testing, documentation, Docker deployment |

---

## 14. Getting Started

```bash
# Clone and setup
git clone https://github.com/yourusername/ask-the-web.git
cd ask-the-web

# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

---

> **Next Steps**: Review this architecture and approve to proceed with Phase 1 implementation.
