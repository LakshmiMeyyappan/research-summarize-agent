# Architectural Decisions & Engineering Design Notes

This document details the core engineering trade-offs, design vectors, and production considerations established during the execution of the Multi-Agent Research Synthesis engine.

##  1. Multi-Step Agent Design (State Machine Architecture)
Instead of relying on a fragile, single-shot prompt wrapper containing all target links, the pipeline is engineered as a deterministic state machine using LangGraph. 

The execution state is decoupled into three highly isolated nodes with a single responsibility principle:
1. Researcher Node (researcher_agent_node): Spawns standard sandboxed browser threads, sanitizes messy document trees, and translates unstructured data into a structured Pydantic array.
2. Analyzer Node (analyzer_agent_node): Takes the consolidated JSON array and focuses strictly on cross-examination metrics (Consensus, Friction/Contradictions, and Missing Omissions).
3. Writer Node (writer_agent_node): Consumes the refined analytical insights to generate a clean, citation-grounded Markdown Brief.

##  2. Web Scraping & Content Engineering Tooling
Real-world enterprise web sources utilize complex client-side dynamic rendering (CSR) and anti-bot network heuristics. 
* Tool Choice: Integrated Playwright running in a headless Chrome environment with spoofed browser user-agents and loose network navigation states (domcontentloaded). This allows the script to bypass initial standard corporate firewalls (e.g., JPMorgan, HBS Working Knowledge) that break traditional basic requests.get() configurations.
* Content Cleaning: Deployed BeautifulSoup to immediately drop non-analytical text noise (<script>, <style>, <nav>, <footer>) before converting to clean Markdown using markdownify.

##  3. Defensive Engineering & Graceful Failure
Web infrastructure is unpredictable. The tool incorporates rigorous automated guardrails:
* Token/TPM Constraint Management: To survive within strict free-tier rate limitations (e.g., Groq's 6,000 TPM limit), two defensive data reduction strategies were implemented. First, the scraper implements a strict character slice ceiling ([:3500]) to capture the analytical heart of the text without data bloat. Second, the pipeline explicitly purges the massive raw_scraped_pages string blocks from the state dictionary container right before it reaches the final formatting stage, reducing context weight by over 60%.
* Exception Isolation: The Playwright engine is wrapped entirely in isolated try/except corridors. If a URL encounters a hard paywall, timeout, or network rejection, it logs a clean [ERROR] descriptor to the console instead of triggering an unhandled engine crash, allowing the state machine to cleanly process all other valid data feeds.

##  4. Production-Scale Considerations & Trade-offs
* In-Memory vs. Persistent State: For the lean MVP scope, LangGraph's standard memory graph-state dictionaries are used. For an enterprise multi-tenant configuration, this would be backed by a persistent datastore (such as Redis or a PostgreSQL checkpointer).
* Hallucination Mitigation: In testing, the synthesis LLM attempted to pull external consulting references (such as McKinsey report models) out of general model parameters. This was handled via a strict, zero-tolerance grounding guardrail prompt. For enterprise production, a hard Pydantic validator filtering output citations against an immutable list of initial input domains would be deployed.
