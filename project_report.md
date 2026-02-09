# Project Report: Axiom AI

> **"Navigate the Web with Intelligence."**

---

## 1. Project Title
**Axiom**
*(Reasoning from first principles. A name that conveys reliability, verification, and logical synthesis.)*

---

## 2. Project Statement
**Axiom** is a **Resume-Ready Full-Stack Web Application** designed to demonstrate advanced engineering capabilities to potential employers. It is an agentic search engine bridging the gap between traditional keyword search and human-like reasoning. By leveraging a multi-provider Large Language Model (LLM) strategy and sophisticated agentic patterns (ReACT, ReWOO), Axiom autonomously plans research, executes web searches, verifies facts, and synthesizes comprehensive answers in real-time. It transforms the overwhelming chaos of the internet into structured, cited, and actionable knowledge, serving as a powerful portfolio piece showcasing skills in AI integration, backend architecture, and modern frontend development.

---

## 3. Objective
The primary objective of **Axiom** is to build a high-impact **Web Application Portfolio Project** that demonstrates your ability to:
1.  **Understands Context**: Goes beyond keywords to understand the intent behind complex queries.
2.  **Reasons Autonomously**: Breaks down complex questions into sub-tasks (planning, searching, synthesizing).
3.  **Provides Verifiable Truth**: delivering answers grounded in real-time web data with explicit source citations.
4.  **Ensures Reliability**: utilizing a dual-provider LLM strategy (NVIDIA NIM + GitHub Models) for high availability and robust fallback mechanisms.
5.  **Delivers Superior UX**: Streaming answers token-by-token to minimize perceived latency.

---

## 4. Scope

### In-Scope
*   **Core Agent**: Implementation of ReACT (Reasoning + Acting) and ReWOO (Reasoning Without Observation) patterns.
*   **Search Integration**: Real-time web search using the Tavily API.
*   **Dual-LLM Strategy**: Abstraction layer for NVIDIA NIM (Primary) and GitHub Models (Fallback).
*   **User Interface**: A modern, responsive Next.js web application with a chat interface.
*   **Streaming**: Server-Sent Events (SSE) for real-time response generation.
*   **Citations**: Automatic extraction and formatting of source citations.
*   **Self-Correction**: Reflexion module to critique and improve answers before delivery.

### Out-of-Scope (for MVP)
*   **User Authentication**: No login required for initial public access (v1).
*   **Payment Processing**: Free-tier usage only.
*   **Mobile Application**: STRICTLY OUT OF SCOPE. This project is exclusively a generic web application to demonstrate full-stack web proficiency.
*   **Complex Multi-Modal Input**: Text-only queries initially (Image input later).

---

## 5. Functional Requirements
1.  **Query Processing**: The system must accept natural language queries from the user.
2.  **Intent Classification**: The system must classify queries as "Simple", "Search", "Research", or "Analysis" to determine the execution path.
3.  **Web Searching**: The system must utilize the Tavily API to fetch relevant web pages and snippets.
4.  **Multi-Step Reasoning**: For complex queries, the system must execute multiple rounds of "Thought → Action → Observation".
5.  **Streaming Response**: The system must push partial updates (tokens, tool usage, thoughts) to the frontend via SSE.
6.  **Fallback Mechanism**: If the primary LLM provider (NVIDIA) fails or errors, the system must seamless retry with the secondary provider (GitHub Models).
7.  **Citation Linking**: All factual claims in the final answer must link to their source URLs.

## 6. Non-Functional Requirements
1.  **Performance**: Time-to-First-Token (TTFT) should be under 2 seconds.
2.  **Reliability**: System uptime target of 99.9%.
3.  **Scalability**: Architecture must support concurrent user sessions via asynchronous processing.
4.  **Maintainability**: Codebase must follow modular design principles (separation of concerns between agents, tools, and UI).
5.  **Security**: API keys must be securely managed via environment variables; no hardcoding.

---

## 7. Tools Required

### Backend Stack
*   **Language**: Python 3.11+
*   **Framework**: FastAPI (High-performance web API)
*   **Server**: Uvicorn (ASGI server)
*   **Orchestration**: Custom Agent Implementation (or LangChain/LangGraph concepts)
*   **Database**: Redis (Caching, Rate Limiting), PostgreSQL (Chat History)

### Frontend Stack
*   **Framework**: Next.js 14 (App Router)
*   **Library**: React.js
*   **Styling**: Tailwind CSS (Utility-first styling)
*   **Icons**: Lucide React
*   **State Management**: React Hooks (specialized for streaming)

### AI & Services
*   **Primary LLM**: NVIDIA NIM (Nemotron-3-Nano-30B for tool calling).
*   **Fallback LLM**: GitHub Models (GPT-4o, Phi-4).
*   **Web Search API**: Tavily Search API (Optimized for LLMs).
*   **Embeddings**: NVIDIA NeMo Retriever / Azure OpenAI Embeddings.

### DevOps & Infrastructure
*   **Containerization**: Docker, Docker Compose.
*   **Version Control**: Git, GitHub.

---

## 8. Step-by-Step Instructions

### Step 1: Environment Setup
1.  Install **Python 3.11+** and **Node.js 18+**.
2.  Install **Docker Desktop** (optional but recommended for Redis/Postgres).
3.  Clone the project repository: `git clone https://github.com/yourusername/axiom.git`.

### Step 2: Configure API Keys
1.  Obtain an API Key from **NVIDIA NIM** (build.nvidia.com).
2.  Obtain an API Key from **GitHub Models** (azure.microsoft.com/en-us/products/ai-services/openai-service).
3.  Obtain an API Key from **Tavily** (tavily.com).
4.  Create a `.env` file in the `backend/` directory and add these keys.

### Step 3: Backend Initialization
1.  Navigate to `backend/`: `cd backend`.
2.  Create a virtual environment: `python -m venv venv`.
3.  Activate it: `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows).
4.  Install dependencies: `pip install -r requirements.txt`.
5.  Start the FastAPI server: `uvicorn app.main:app --reload`.

### Step 4: Frontend Initialization
1.  Open a new terminal and navigate to `frontend/`: `cd frontend`.
2.  Install dependencies: `npm install`.
3.  Start the development server: `npm run dev`.
4.  Open `http://localhost:3000` in your browser.

### Step 5: Verification & Testing
1.  **Simple Test**: Ask "What is the capital of France?" (Should respond instantly without search).
2.  **Search Test**: Ask "Who won the latest Super Bowl?" (Should show "Searching..." then answer with citations).
3.  **Complex Test**: Ask "Compare the features of iPhone 16 and Samsung S25." (Should perform multiple searches and synthesize a comparison).

---

## 9. Concepts to Learn
To successfully build and accept this project, you should familiarize yourself with:

1.  **Agentic AI Patterns**:
    *   **ReACT**: How to loop "Thought, Action, Observation".
    *   **ReWOO**: Planning ahead to reduce latency.
    *   **Reflexion**: Self-critique to fix hallucinations.

2.  **RAG (Retrieval-Augmented Generation)**:
    *   How to retrieve relevant documents and feed them into the LLM's context window.
    *   **Vector Embeddings**: Converting text to numbers for semantic search.

3.  **Asynchronous Programming (Async/Await)**:
    *   Python's `asyncio` library is critical for handling multiple concurrent agents and tool calls without blocking.

4.  **Server-Sent Events (SSE)**:
    *   Understanding how to stream data from server to client in real-time (unlike WebSockets, SSE is uni-directional and simpler for this use case).

5.  **Prompt Engineering**:
    *   How to craft system prompts that force the LLM to output structured data (JSON) or follow specific reasoning steps.

---
**Prepared by**: Antigravity (Google Deepmind)
**Date**: October 26, 2023
