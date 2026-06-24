import os
import asyncio
from typing import List, Dict, Any, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- Web Scraping & Content Cleaning Libraries ---
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import markdownify

# --- LangChain & LangGraph Orchestration ---
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END

# Load Environment Variables from a .env file
load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("CRITICAL ERROR: Please define GROQ_API_KEY in your environment or .env file.")

# Initialize Groq LLM (Using the fast, stable 8b model)
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

# =====================================================================
# 🗂️ 1. DATA SCHEMA DEFINITIONS
# =====================================================================

class SingleSourceAnalysis(BaseModel):
    source_url: str = Field(description="The source URL being evaluated.")
    main_thesis: str = Field(description="A 2-sentence summary of the author's primary perspective.")
    claims: List[str] = Field(description="List of explicit, distinct factual assertions made by the source text.")

class CrossSourceInsight(BaseModel):
    consensus_claims: List[str] = Field(description="Claims directly supported or verified by two or more sources.")
    outlier_claims: List[str] = Field(description="Unique or major assertions made exclusively by exactly ONE source.")
    contradictions: List[str] = Field(description="Direct disagreements, data friction, or mismatched statements found between sources.")
    unaddressed_gaps: List[str] = Field(description="Crucial sub-topics regarding the main prompt that no source discussed.")

class AgentPipelineContainer(TypedDict):
    topic: str
    urls: List[str]
    raw_scraped_pages: Dict[str, str]
    structured_claims: List[Dict[str, Any]]
    cross_source_matrix: Dict[str, Any]
    final_markdown_brief: str

# =====================================================================
# 🌐 2. BROWSER SCRAPING TOOL (Hardened for Free-Tier Token Budgets)
# =====================================================================

async def scrape_and_clean_tool(url: str) -> str:
    """
    Advanced Playwright Tool: Features custom anti-bot behavior, 
    stringent token control, and clean markdown conversions.
    """
    print(f"   🌐 [Scraper Tool] Dynamically fetching: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                }
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000) 
            content = await page.content()
            await browser.close()
            
            soup = BeautifulSoup(content, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "aside"]):
                element.decompose()
            
            cleaned_md = markdownify.markdownify(str(soup), heading_style="ATX")
            processed_lines = [line.strip() for line in cleaned_md.splitlines() if line.strip()]
            full_text = "\n".join(processed_lines)
            
            # --- TOKEN FIX 1 ---
            # Lowering the character limit ceiling to 3,500 characters. 
            # This captures the analytical heart of the text while ensuring we stay miles below the 6,000 token ceiling.
            return full_text[:3500]
            
    except Exception as e:
        return f"[ERROR] Could not fetch or load live page structure. Reason: {str(e)}"

# =====================================================================
# 🤖 3. AGENT PIPELINE NODES
# =====================================================================

async def researcher_agent_node(state: AgentPipelineContainer) -> Dict[str, Any]:
    print("\n🕵️ [Agent 1] Researcher: Initiating data gathering and factual claim extraction...")
    
    scraped_pages = {}
    structured_claims = []
    parser = JsonOutputParser(pydantic_object=SingleSourceAnalysis)
    
    for url in state["urls"]:
        raw_text = await scrape_and_clean_tool(url)
        scraped_pages[url] = raw_text
        
        if raw_text.startswith("[ERROR]"):
            print(f"   ⚠️ Skipping claim extraction for {url} due to loading error.")
            continue
            
        print(f"   🔎 Extracting discrete factual structures from: {url}")
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an Elite Forensic Research Agent. Read the text and extract the core factual claims regarding the topic: '{topic}'. You MUST respond with a valid JSON object matching the requested schema instructions.\n{format_instructions}"),
            ("user", "Source URL: {url}\n\nRaw Page Text Material:\n{text}")
        ])
        
        formatted_prompt = prompt_template.format_messages(
            topic=state["topic"],
            url=url,
            text=raw_text,
            format_instructions=parser.get_format_instructions()
        )
        
        try:
            response = await llm.ainvoke(formatted_prompt)
            parsed_json = parser.parse(response.content)
            
            if "source_url" not in parsed_json or not parsed_json["source_url"]:
                parsed_json["source_url"] = url
                
            structured_claims.append(parsed_json)
            print(f"   ✅ Successfully structured claims for: {url}")
        except Exception as e:
            print(f"   ❌ JSON Parsing failed for {url}. Details: {e}")
            
    return {
        "raw_scraped_pages": scraped_pages, 
        "structured_claims": structured_claims
    }


async def analyzer_agent_node(state: AgentPipelineContainer) -> Dict[str, Any]:
    print("\n🧠 [Agent 2] Analyzer: Cross-examining facts to isolate contradictions, consensus, and gaps...")
    
    # We use a direct, high-reasoning prompt to force the model to uncover friction points
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a Chief Strategic Intelligence Officer. Perform a deep cross-examination over the provided research data on the topic: '{topic}'.
        
        Analyze the claims deeply to isolate:
        1. CONSENSUS: Where do multiple sources clearly agree?
        2. CONTRADICTIONS: Where do sources flat-out disagree, provide conflicting numbers, or show strategic friction? (e.g., source 1 says junior jobs are being destroyed right now, while source 3 claims a massive net gain of millions of jobs). Look closely at numbers, timelines, and impact severity.
        3. OUTLIERS: What major claims are made by ONLY one single source?
        4. UNADDRESSED GAPS: What critical sub-topics regarding AI labor impact (like wage changes, specific geographic discrepancies, or retraining costs) did ALL 5 sources completely ignore?
        
        Provide your output as a clean Python-readable dictionary structure with string fields. No markdown wrappers."""),
        ("user", "Collected Fact Claims Data:\n{claims_data}")
    ])
    
    formatted_prompt = prompt_template.format_messages(
        topic=state["topic"],
        claims_data=str(state["structured_claims"])
    )
    
    try:
        response = await llm.ainvoke(formatted_prompt)
        # We pass the raw analysis text directly to the state container
        # This completely bypasses schema-validation errors while preserving 100% of the logical synthesis
        return {"cross_source_matrix": {"raw_analysis": response.content}}
    except Exception as e:
        print(f"   ❌ Analyzer parsing failed. Using fallback. Details: {e}")
        return {"cross_source_matrix": {"raw_analysis": "Analytical synthesis pass failed due to processing limits."}}


async def writer_agent_node(state: AgentPipelineContainer) -> Dict[str, Any]:
    print("\n✍️ [Agent 3] Writer: Rendering final polished executive markdown brief...")
    
    clean_claims = []
    for item in state["structured_claims"]:
        clean_claims.append({
            "source_url": item.get("source_url", ""),
            "main_thesis": item.get("main_thesis", ""),
            "claims": item.get("claims", [])
        })

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an Expert PM Ghostwriter. Synthesize the provided claim data and cross-examination analysis into a clean executive Markdown Briefing document.
        
        🔴 STAGE-GATE GUARDRAILS (ZERO HALLUCINATION TOLERANCE):
        1. Ground 100% of your text in the provided source data. Do NOT use outside training knowledge.
        2. Do NOT invent external entities, consulting firms (e.g., McKinsey), or statistics not explicitly listed in the inputs.
        3. If data or a contradiction is missing from a source, report it transparently rather than fabricating a filler stat.
        4. Every factual point must use short domain inline citations matching the input links (e.g., [yale.edu], [brookings.edu]). No conversational fluff."""),
        ("user", "Target Subject: {topic}\n\nRaw Fact Matrix Structure:\n{raw_claims}\n\nCross-Source Intersections and Analysis:\n{cross_matrix}")
    ])
    
    formatted_prompt = prompt_template.format_messages(
        topic=state["topic"],
        raw_claims=str(clean_claims),
        cross_matrix=str(state["cross_source_matrix"].get("raw_analysis", ""))
    )
    
    response = await llm.ainvoke(formatted_prompt)
    return {"final_markdown_brief": response.content}

# =====================================================================
# 🕸️ 4. LANGGRAPH WORKFLOW ORCHESTRATION
# =====================================================================

def compile_agent_workflow():
    workflow = StateGraph(AgentPipelineContainer)
    
    workflow.add_node("researcher", researcher_agent_node)
    workflow.add_node("analyzer", analyzer_agent_node)
    workflow.add_node("writer", writer_agent_node)
    
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyzer")
    workflow.add_edge("analyzer", "writer")
    workflow.add_edge("writer", END)
    
    return workflow.compile()

# =====================================================================
# 🚀 5. EXECUTION ENTRYPOINT
# =====================================================================

async def main():
    target_topic = "The real impact of AI on the labor market, displacement, and job creation timelines"
    
    target_urls = [
        "https://insights.som.yale.edu/insights/the-real-job-destruction-from-ai-is-hitting-before-careers-can-start",
        "https://www.library.hbs.edu/working-knowledge/enhance-or-eliminate-how-ai-will-likely-change-these-jobs",
        "https://gloat.com/blog/ai-labor-market/",
        "https://www.brookings.edu/articles/measuring-us-workers-capacity-to-adapt-to-ai-driven-job-displacement/",
        "https://www.jpmorgan.com/insights/global-research/artificial-intelligence/ai-impact-job-growth"
    ]
    
    initial_state: AgentPipelineContainer = {
        "topic": target_topic,
        "urls": target_urls,
        "raw_scraped_pages": {},
        "structured_claims": [],
        "cross_source_matrix": {},
        "final_markdown_brief": ""
    }
    
    app = compile_agent_workflow()
    print("🔥 Multi-Agent State Graph Engine Activated via LangGraph (Hardened Production Build).")
    
    final_output_state = await app.ainvoke(initial_state)
    
    output_filename = "final_research_brief.md"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(final_output_state["final_markdown_brief"])
        
    print(f"\n🎉 SUCCESS! Your genuine PM Brief has been compiled to: '{output_filename}'")

if __name__ == "__main__":
    asyncio.run(main())