from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
Gemini.api_key = os.getenv("GOOGLE_API_KEY")

## Web Search Agent
web_search_agent = Agent(
    name="Web Search Agent",
    role="Search the web for accurate and up-to-date financial information",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[DuckDuckGo()],
    instructions=[
        "1. Perform targeted searches to find the most relevant and recent financial information.",
        "2. Always verify the credibility of sources before including them in the response.",
        "3. Summarize the information concisely and include direct links to the sources.",
        "4. If no relevant information is found, state this clearly and suggest alternative search terms.",
    ],
    show_tool_calls=True,
    markdown=True,
)

## Financial Agent
financial_agent = Agent(
    name="Finance AI Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[
        YFinanceTools(
            stock_price=True,
            stock_fundamentals=True,
            analyst_recommendations=True,
            company_news=True,
        )
    ],
    instructions=[
        "1. Use tables to display stock data for better readability.",
        "2. Always include the following details for any stock:",
        "   - Current price",
        "   - Key fundamentals (e.g., P/E ratio, market cap)",
        "   - Latest analyst recommendations (Buy/Hold/Sell)",
        "   - Recent company news (last 7 days)",
        "3. If data is unavailable, explain why and suggest alternative tools or sources.",
        "4. Keep the response concise and avoid unnecessary details.",
    ],
    show_tool_calls=True,
    markdown=True,
)

## Multi-AI Agent
multi_ai_agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    team=[web_search_agent, financial_agent],
    instructions=[
        "1. Use the web search agent to find the latest financial news and updates.",
        "2. Use the financial agent to analyze stock data and provide structured insights.",
        "3. Always combine the results from both agents into a single, cohesive response.",
        "4. Follow these formatting guidelines:",
        "   - Use headings to separate sections (e.g., 'Latest News', 'Stock Analysis').",
        "   - Use tables for numerical data.",
        "   - Include clickable links for all sources.",
        "5. If the user's query is unclear, ask for clarification before proceeding.",
    ],
    show_tool_calls=True,
    markdown=True,
)

# Example Query
multi_ai_agent.print_response(
    "Summarize analyst recommendations and share the latest news for NVIDIA Corporation (NVDA).",
    stream=True,
    )