# Multi-Agent Research Synthesis Engine (MVP)

A modular, production-ready research pipeline built with multi agents, LangGraph, Playwright, and Groq (llama-3.1-8b-instant) to automate source scraping, factual claim extraction, and cross-source synthesis into a single executive markdown brief.

##  Core Capabilities
* State Machine Coordination: Built using LangGraph to isolate task execution into distinct, single-responsibility steps: Research Extraction -> Strategic Analysis -> Executive Writing.
* Resilient Web Scraping: Leverages headless Playwright sessions configured with custom headers to safely extract data from JavaScript-heavy corporate and academic research portals.
* Friction & Gap Detection: Programmed to cross-examine text blocks specifically for consensus patterns, direct factual contradictions, and overlooked industry gaps.
* Token-Aware Context Engineering: Automatically trims and drops heavy raw HTML/Markdown code blocks out of the graph state before formatting, ensuring smooth execution under strict API rate limits.

---

##  Repository Layout
* main.py - The single-file multi-agent workflow architecture, browser scraper, and orchestration entry point.
* final_research_brief.md - The generated, client-ready analytical markdown briefing document.
* NOTES.md - Engineering notes outlining architectural choices, trade-offs, and scaling plans.
* prompts.md - Transcript archive logging the prompt sequences used to shape and build the pipeline.
* requirements.txt - Python package dependency manifest.
* .env - Sandboxed API credentials storage.

---

##  Setup and Installation

### 1. Initialize and Activate Virtual Environment
Navigate to your project directory and set up a virtual environment to isolate your dependencies:
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On Mac/Linux:
source .venv/bin/activate

### 2. Install Dependencies and Browser Drivers
Install the required packages and configure Playwright's headless browser binaries:
pip install -r requirements.txt
playwright install chromium

### 3. Environment Configuration
Create a file named exactly .env in the root folder of the project and add your Groq API token:
GROQ_API_KEY=your_actual_groq_api_key_here

### 4. Run the Script
Execute the script via your active terminal to trigger the graph pipeline:
python main.py

---

##  Operational Pipeline Flow
1. Researcher Agent: Opens browser sandboxes asynchronously, strips page clutter (navbars, scripts), applies text bounds, and builds structured claim sets.
2. Analyzer Agent: Consolidates the claim library to locate data intersections, unique claims, and unaddressed topics.
3. Writer Agent: Packages the consolidated insights into a cleanly formatted, highly skimmable executive document.
