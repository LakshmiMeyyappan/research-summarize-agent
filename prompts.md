# AI-Native Development Log & Prompt Transcripts

This file documents the core prompts, structural updates, and prompt engineering steps used to guide the AI while building this research agent.

---

##  Step 1: Playwright Scraper Tool Optimization
**Goal**: Build a resilient web scraper capable of extracting clean text from complex or JavaScript-heavy domains (like HBS or JPMorgan) without getting blocked.

### The System Prompt:
You are an expert systems engineer building an enterprise web scraper using Playwright. 
Write an asynchronous Python function that visits a target URL using a customized desktop User-Agent string and extra browser headers to prevent basic bot-detection blocks. 
The function must use BeautifulSoup to strip away non-content tags like <script>, <style>, <nav>, and <footer>, and return the core article body text cleaned and truncated to protect downstream token limits.

---

##  Step 2: Mitigating Rate Limits (Context Pruning)
**Goal**: Prevent Error code: 413 - Request too large on free-tier inference keys when synthesizing multiple dense text sources simultaneously.

### The System Prompt:
Modify the LangGraph state orchestration step. Before the structured data is passed to the final writing agent, create an automated clean-up step in the state pipeline. Take the structured JSON claims from Agent 1 and discard the massive 'raw_scraped_pages' text blocks entirely. This ensures that the context window passed to the final LLM node contains only high-density factual insights, dropping token weight by over 60%.

---

##  Step 3: Eliminating Hallucinations in the Output Layer
**Goal**: Prevent the writing agent from introducing external training data or hallucinating external references (such as unprovided consulting group names or fake statistical figures).

### The System Prompt (Writer Node Guide):
You are an Expert Product Manager Ghostwriter. You have a zero-tolerance guardrail for text hallucinations. Synthesize the provided claim data and cross-examination notes into a clean, executive Markdown Briefing document.

STRICT ACCURACY RULES:
1. Ground 100% of your statements in the provided source text. Do NOT use outside training knowledge.
2. Do NOT invent external entities, consulting firms, or specific statistics not explicitly written in the input data.
3. If data is missing or if no direct contradictions are identified in the text, report that transparently instead of creating filler information.
4. Every factual note must use clear domain inline citations matching the input links (e.g., [yale.edu], [brookings.edu]).
