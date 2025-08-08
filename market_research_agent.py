"""
Market Research Agent - Cost-efficient market analysis at market open
Uses web scraping and Groq/LangChain for AI analysis
"""

import os
import asyncio
import aiohttp
import markdown2
from datetime import datetime, time
from typing import Dict, List, Any
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

load_dotenv()


class MarketDataCollector:
    """Collects market data from various free sources"""
    
    def __init__(self):
        self.session = None
        self.fmp_api_key = os.getenv('FMP_API_KEY')

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def _fetch_with_retry(self, url, source):
        for attempt in range(3):
            try:
                async with self.session.get(url, timeout=10) as response:
                    response.raise_for_status() # Will raise an exception for 4xx/5xx status
                    return await response.text()
            except aiohttp.ClientError as e:
                print(f"Attempt {attempt + 1} failed for {source}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
        return None

    async def fetch_headlines(self) -> List[str]:
        """Fetch comprehensive financial and macroeconomic headlines from multiple FMP sources"""
        if not self.fmp_api_key:
            print("FMP API key not found.")
            return []

        all_headlines = []
        
        # Define multiple news sources for comprehensive coverage
        news_sources = {
            'stock_news': f"https://financialmodelingprep.com/stable/news/stock-latest?page=0&limit=100&apikey={self.fmp_api_key}",
            'forex_news': f"https://financialmodelingprep.com/stable/news/forex-latest?page=0&limit=20&apikey={self.fmp_api_key}",
            'crypto_news': f"https://financialmodelingprep.com/stable/news/crypto-latest?page=0&limit=20&apikey={self.fmp_api_key}",
            'general_news': f"https://financialmodelingprep.com/stable/news/general-latest?page=0&limit=100&apikey={self.fmp_api_key}",
        }
        
        # Fetch from each source
        for source_name, url in news_sources.items():
            print(f"Attempting to fetch from {source_name}...")
            try:
                async with self.session.get(url) as response:
                    print(f"Response status for {source_name}: {response.status}")
                    response.raise_for_status()
                    data = await response.json()
                    
                    print(f"Data type for {source_name}: {type(data)}")
                    if data:
                        print(f"First few items from {source_name}: {str(data)[:200]}...")
                    
                    if data and isinstance(data, list):
                        headlines = [item['title'] for item in data if 'title' in item and item['title']]
                        all_headlines.extend(headlines)
                        print(f"✓ Fetched {len(headlines)} headlines from {source_name}")
                    elif data and isinstance(data, dict):
                        # Some endpoints might return a dict with a 'data' or 'articles' key
                        if 'data' in data:
                            headlines = [item['title'] for item in data['data'] if 'title' in item and item['title']]
                            all_headlines.extend(headlines)
                            print(f"✓ Fetched {len(headlines)} headlines from {source_name} (dict format)")
                        else:
                            print(f"⚠ {source_name} returned dict but no 'data' key. Keys: {list(data.keys())}")
                    else:
                        print(f"⚠ {source_name} returned unexpected format or empty data")
                    
            except aiohttp.ClientResponseError as e:
                print(f"✗ HTTP error fetching {source_name}: {e.status} - {e.message}")
                if e.status == 403:
                    print(f"  → {source_name} might not be available on your FMP subscription tier")
                elif e.status == 429:
                    print(f"  → Rate limited on {source_name}")
                continue
            except aiohttp.ClientError as e:
                print(f"✗ Client error fetching {source_name}: {e}")
                continue
            except Exception as e:
                print(f"✗ Unexpected error fetching {source_name}: {e}")
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_headlines = []
        for headline in all_headlines:
            if headline and headline not in seen:
                seen.add(headline)
                unique_headlines.append(headline)
        
        print(f"📊 Total unique headlines collected: {len(unique_headlines)}")
        
        # Return up to 300 headlines for the AI to filter through
        return unique_headlines[:300]

    async def fetch_yields(self) -> Dict[str, float]:
        """Fetch current treasury yields from FMP"""
        return await asyncio.to_thread(self._fetch_yields_sync)

    def _fetch_yields_sync(self) -> Dict[str, float]:
        yields = {}
        symbols = {
            'US 13W': '^IRX',      # 13 Week Treasury Bill
            'US 5Y': '^FVX',      # 5 Year Treasury Note
            'US 10Y': '^TNX',     # 10 Year Treasury Note
            'US 30Y': '^TYX',     # 30 Year Treasury Bond
        }
        try:
            for name, symbol in symbols.items():
                url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={self.fmp_api_key}"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data:
                    yields[name] = data[0].get('price')
            return yields
        except Exception as e:
            print(f"Error fetching yields from FMP: {e}")
            return {}

    async def fetch_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Fetch major market benchmarks from FMP"""
        return await asyncio.to_thread(self._fetch_benchmarks_sync)

    def _fetch_benchmarks_sync(self) -> Dict[str, Dict[str, Any]]:
        benchmarks = {}
        symbols = [
            # US Major Indices
            '^GSPC',    # S&P 500
            '^DJI',     # Dow Jones Industrial Average
            '^IXIC',    # NASDAQ Composite
            '^RUT',     # Russell 2000
            '^VIX',     # Volatility Index
            'SPY',     # S&P 500 ETF
            

            
            # Global Indices
            '^FTSE',    # FTSE 100 (UK)
            '^N225',    # Nikkei 225 (Japan)
            '^GDAXI',   # DAX (Germany)
            '^FCHI',    # CAC 40 (France)
            '^HSI',     # Hang Seng (Hong Kong)
            '^AXJO',    # ASX 200 (Australia)
            '^BVSP',    # Bovespa (Brazil)
            '^MXX',     # IPC Mexico
            
            # Sector ETFs
            'XLF',      # Financial Select Sector SPDR
            'XLK',      # Technology Select Sector SPDR
            'XLE',      # Energy Select Sector SPDR
            'XLV',      # Health Care Select Sector SPDR
            'XLI',      # Industrial Select Sector SPDR
            'XLP',      # Consumer Staples Select Sector SPDR
            'XLY',      # Consumer Discretionary Select Sector SPDR
            'XLU',      # Utilities Select Sector SPDR
            'XLRE',     # Real Estate Select Sector SPDR
            'XLB',      # Materials Select Sector SPDR
            
            # Commodities
            'CL=F',     # Crude Oil WTI
            'BZ=F',     # Brent Crude Oil
            'NG=F',     # Natural Gas
            'GC=F',     # Gold
            'SI=F',     # Silver
            'HG=F',     # Copper
            'PL=F',     # Platinum
            'PA=F',     # Palladium
            'ZC=F',     # Corn
            'ZW=F',     # Wheat
            'ZS=F',     # Soybeans
            
            # Currencies
            'EURUSD=X', # EUR/USD
            'GBPUSD=X', # GBP/USD
            'USDJPY=X', # USD/JPY
            'USDCAD=X', # USD/CAD
            'AUDUSD=X', # AUD/USD
            'USDCHF=X', # USD/CHF
            'NZDUSD=X', # NZD/USD
            'USDSEK=X', # USD/SEK
            'USDNOK=X', # USD/NOK
            'DX-Y.NYB', # US Dollar Index
            
            # Cryptocurrency
            'BTC-USD',  # Bitcoin
            'ETH-USD',  # Ethereum
            'ADA-USD',  # Cardano
            'SOL-USD',  # Solana

            # Bonds & Fixed Income
            'TLT',      # 20+ Year Treasury Bond ETF
            'IEF',      # 7-10 Year Treasury Bond ETF
            'SHY',      # 1-3 Year Treasury Bond ETF
            'HYG',      # High Yield Corporate Bond ETF
            'LQD',      # Investment Grade Corporate Bond ETF
            'EMB',      # Emerging Markets Bond ETF
            
            # Alternative Assets
            'REIT',     # iShares Core U.S. REIT ETF
            'PDBC',     # Invesco Optimum Yield Diversified Commodity Strategy No K-1 ETF
            'IAU',      # iShares Gold Trust
            'SLV',      # iShares Silver Trust
        ]
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{','.join(symbols)}?apikey={self.fmp_api_key}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            for item in data:
                benchmarks[item['name']] = {
                    'price': item.get('price'),
                    'change': item.get('change'),
                    'change_pct': f"{item.get('changesPercentage', 0):.2f}"
                }
            return benchmarks
        except Exception as e:
            print(f"Error fetching benchmarks from FMP: {e}")
            return {}

    async def fetch_major_movers(self) -> List[Dict[str, Any]]:
        """Fetch top gainers and losers from FMP"""
        return await asyncio.to_thread(self._fetch_major_movers_sync)

    def _fetch_major_movers_sync(self) -> List[Dict[str, Any]]:
        movers = []
        
        # Try to get most active stocks and sort by biggest intraday moves
        try:
            # Get most active stocks (these often include the biggest intraday movers)
            actives_url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={self.fmp_api_key}"
            response = requests.get(actives_url)
            response.raise_for_status()
            actives_data = response.json()
            
            if actives_data:
                # Sort by absolute percentage change to get biggest movers
                sorted_by_change = sorted(actives_data[:50], 
                                        key=lambda x: abs(x.get('changesPercentage', 0)), 
                                        reverse=True)
                
                # Separate into gainers and losers, taking top 10 of each
                gainers = [item for item in sorted_by_change if item.get('changesPercentage', 0) > 0][:10]
                losers = [item for item in sorted_by_change if item.get('changesPercentage', 0) < 0][:10]
                
                # Add gainers
                for item in gainers:
                    movers.append({
                        'symbol': item['symbol'],
                        'name': item['name'],
                        'change_pct': f"{item['changesPercentage']:.2f}%",
                        'price': item.get('price', 'N/A'),
                        'volume': item.get('volume', 'N/A'),
                        'type': 'gainers'
                    })
                
                # Add losers
                for item in losers:
                    movers.append({
                        'symbol': item['symbol'],
                        'name': item['name'],
                        'change_pct': f"{item['changesPercentage']:.2f}%",
                        'price': item.get('price', 'N/A'),
                        'volume': item.get('volume', 'N/A'),
                        'type': 'losers'
                    })
                
                if movers:  # If we got data, return it
                    return movers
                    
        except Exception as e:
            print(f"Error fetching active stocks, falling back to regular movers: {e}")
        
        # Fallback to regular gainers/losers if actives API fails
        urls = {
            'gainers': f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={self.fmp_api_key}",
            'losers': f"https://financialmodelingprep.com/api/v3/stock_market/losers?apikey={self.fmp_api_key}"
        }
        try:
            for move_type, url in urls.items():
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                for item in data[:10]:
                    movers.append({
                        'symbol': item['symbol'],
                        'name': item['name'],
                        'change_pct': f"{item['changesPercentage']:.2f}%",
                        'type': move_type
                    })
            return movers
        except Exception as e:
            print(f"Error fetching movers from FMP: {e}")
            return []


class MarketResearchAgent:
    """Main agent that coordinates data collection and analysis"""
    
    def __init__(self):
        # Primary model
        self.primary_llm = ChatGroq(
            api_key=os.getenv('GROQ_API_KEY'),
            model='openai/gpt-oss-120b',
            temperature=0.1,
        )
        
        # Fallback model
        self.fallback_llm = ChatGroq(
            api_key=os.getenv('GROQ_API_KEY'),
            model='llama-3.3-70b-versatile',
            temperature=0.1,
        )
        
        self.current_llm = self.primary_llm  # Start with primary model

    async def _try_llm_with_fallback(self, chain, input_data, max_retries=2):
        """Try the primary LLM, fall back to secondary if it fails"""
        
        # Try primary model first
        try:
            print("🤖 Attempting analysis with primary model (openai/gpt-oss-120b)...")
            primary_chain = LLMChain(llm=self.primary_llm, prompt=chain.prompt)
            response = await primary_chain.ainvoke(input_data)
            print("✅ Primary model succeeded")
            return response
            
        except Exception as e:
            print(f"⚠️ Primary model failed: {e}")
            print("🔄 Falling back to llama-3.3-70b-versatile...")
            
            try:
                fallback_chain = LLMChain(llm=self.fallback_llm, prompt=chain.prompt)
                response = await fallback_chain.ainvoke(input_data)
                print("✅ Fallback model succeeded")
                return response
                
            except Exception as fallback_error:
                print(f"❌ Fallback model also failed: {fallback_error}")
                raise Exception(f"Both models failed. Primary: {e}, Fallback: {fallback_error}")

    async def analyze_market(self) -> str:
        """Collect data and generate market analysis as a formatted string"""
        async with MarketDataCollector() as collector:
            tasks = {
                'headlines': collector.fetch_headlines(),
                'yields': collector.fetch_yields(),
                'benchmarks': collector.fetch_benchmarks(),
                'movers': collector.fetch_major_movers(),
            }
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        headlines, yields, benchmarks, movers = results
        
        # Handle exceptions and provide debugging info
        if isinstance(headlines, Exception):
            print(f"Headlines fetch failed: {headlines}")
            headlines = []
        if isinstance(yields, Exception):
            print(f"Yields fetch failed: {yields}")
            yields = {}
        if isinstance(benchmarks, Exception):
            print(f"Benchmarks fetch failed: {benchmarks}")
            benchmarks = {}
        if isinstance(movers, Exception):
            print(f"Movers fetch failed: {movers}")
            movers = []

        # Debug output
        print(f"Data collected - Headlines: {len(headlines)}, Yields: {len(yields)}, Benchmarks: {len(benchmarks)}, Movers: {len(movers)}")
        if headlines:
            print(f"Sample headlines: {headlines[:3]}")
        if benchmarks:
            print(f"Sample benchmarks: {list(benchmarks.keys())[:3]}")

        # --- Data Validation and Circuit Breaker ---
        if not any([headlines, yields, benchmarks, movers]):
            error_message = "Failed to collect any market data. All sources may be down or API keys invalid. Aborting analysis."
            print(error_message)
            return error_message

        # Format data for the prompt
        formatted_yields = "\n".join([f"{name}: {value:.2f}%" for name, value in yields.items()]) if yields else "Data not available."
        formatted_benchmarks = "\n".join([f"- {name}: {details['price']} ({details['change_pct']} %)" for name, details in benchmarks.items()]) if benchmarks else "Data not available."
        formatted_movers = "\n".join([f"- {mover['name']} ({mover['symbol']}): {mover['change_pct']} ({mover['type']})" for mover in movers]) if movers else "Data not available."

        prompt_template = ChatPromptTemplate.from_template(
            """You are a genius, insightful financial analyst with years of experience providing a morning market briefing for {current_date}. Your tone should be conversational yet informative, like a pro talking to colleagues.

**Crucial Instructions:**
- **DO NOT HALLUCINATE.** Use ONLY the data provided below. Do not invent facts, figures, or news.
- If data for a section is unavailable, state "Data not available."
- Your analysis must be insightful, connecting different data points.
- The News section is critical. It should be the most in-depth, discussing 15-25 most important and interesting headlines (MAXIMUM 25 HEADLINES) DO NOT LIST MORE THAN 25 HEADLINES UNDER ANY CIRCUMSTANCE. DO NOT include earnings call transcripts in this section, or any other transcripts, we want interesting macro and market headlines.
- Please try to include current prices for the major indices IF AVAILABLE.

TO REPEAT:
- NO EARNINGS CALL TRANSCRIPTS IN THE NEWS SECTION UNDER ANY CIRCUMSTANCE. IF IT HAS "earnings call transcript" OR SIMILAR IN THE HEADLINE DO NOT INCLUDE IT.
- MAXIMUM 25 HEADLINES, CAREFULLY SELECT THE MOST INTERESTING AND IMPORTANT HEADLINES
- Try to keep headlines that are most important and interesting to economic markets and geopolitics.

WHEN DECIDING WHICH HEADLINES TO INCLUDE, CONSIDER THE FOLLOWING:
- Is it a fact or opinion? Prioritize facts
- Is it relevant to the market? Prioritize market-relevant news
- Is it related to geopolitics and macroeconomic trends? Prioritize geopolitical news
- Is it related to technology and innovation? Prioritize technology news
- Is it related to consumer behavior and trends? Prioritize consumer news
- Is it related to the economy and economy? Prioritize economy news
AVOID:
- Headlines that are questions
- Headlines that don't necessarily highlight any market-moving information

**Market Data for your analysis:**
- **Headlines:**
{headlines}
- **Treasury Yields:**
{formatted_yields}
- **Market Benchmarks:**
{formatted_benchmarks}
- **MAJOR MOVERS:**
{formatted_movers}

**CRITICAL: You MUST use these EXACT section headers in your response:**
- **📈 Markets:**
- **📰 Top News:**
- **🚀 Major Movers 📉:**
- **💡 Key Takeaways:**
- **📊 Overall Sentiment:**

Please provide a detailed report in the style of a professional market briefing. Please avoid using charts or diagrams, instead just use markdown / plain speech.

        """
        )
        
        chain = LLMChain(llm=self.current_llm, prompt=prompt_template)
        
        try:
            # Using ainvoke which is the new standard for async calls
            input_data = {
                "current_date": datetime.now().strftime("%A, %B %d, %Y"),
                "headlines": "\n".join(headlines) if headlines else "Data not available.",
                "formatted_yields": formatted_yields,
                "formatted_benchmarks": formatted_benchmarks,
                "formatted_movers": formatted_movers
            }
            response = await self._try_llm_with_fallback(chain, input_data)
            # The response from ainvoke is a dictionary, we need to get the 'text' key
            analysis = response.get('text', 'Error: Could not generate analysis.')
            
            # Debugging the final prompt and response
            final_prompt = prompt_template.format(**input_data)
            print("\n--- Final Prompt Sent to AI ---\n")
            print(final_prompt)
            print("\n--- AI Response ---\n")
            print(analysis)
            
            return analysis

        except Exception as e:
            error_message = f"An error occurred during AI analysis: {e}"
            print(error_message)
            return error_message

    def format_email_content(self, analysis: str) -> str:
        """Formats the AI analysis into a professional HTML email."""
        # Convert markdown analysis to HTML
        # Using extras for better formatting, like tables and fenced code blocks
        content_html = markdown2.markdown(
            analysis, 
            extras=["tables", "fenced-code-blocks", "cuddled-lists", "break-on-newline"]
        )

        # Get the current date for the email subject and header
        current_date_str = datetime.now().strftime("%B %d, %Y")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Market Research Report</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .header .date {{
                    margin: 10px 0 0 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                .content {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                .section {{
                    margin-bottom: 30px;
                    border-left: 4px solid #e9ecef;
                    padding-left: 20px;
                }}
                .markets-section {{
                    border-left-color: #28a745;
                }}
                .news-section {{
                    border-left-color: #007bff;
                }}
                .movers-section {{
                    border-left-color: #ffc107;
                }}
                .takeaways-section {{
                    border-left-color: #17a2b8;
                }}
                .sentiment-section {{
                    border-left-color: #6f42c1;
                }}
                .section-header {{
                    color: #2c3e50;
                    font-size: 20px;
                    font-weight: 600;
                    margin: 0 0 15px 0;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e9ecef;
                }}
                .section-content {{
                    font-size: 14px;
                }}
                .market-item {{
                    background: #f8f9fa;
                    padding: 8px 12px;
                    margin: 5px 0;
                    border-radius: 5px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 13px;
                    border-left: 3px solid #28a745;
                }}
                .bullet-point {{
                    margin: 8px 0;
                    padding-left: 15px;
                    position: relative;
                }}
                .bullet-point:before {{
                    content: "•";
                    color: #007bff;
                    font-weight: bold;
                    position: absolute;
                    left: 0;
                }}
                .content-paragraph {{
                    margin: 12px 0;
                    line-height: 1.7;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 10px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .footer a {{
                    color: #007bff;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Market Research Report</h1>
                <div class="date">{current_date_str}</div>
            </div>
            
            <div class="content">
                {content_html}
            </div>
            
            <div class="footer">
                <p>This report was generated automatically by your Market Research Agent.</p>
                <p>Powered by Financial Modeling Prep API & Groq AI</p>
            </div>
        </body>
        </html>
        """
        return html


async def main():
    """Main function to run the market research agent"""
    agent = MarketResearchAgent()
    analysis = await agent.analyze_market()
    
    # Print summary to console
    print("\n=== Market Research Summary ===")
    print(analysis)
    
    # Generate email content (ready for sending)
    email_content = agent.format_email_content(analysis)
    
    # Save to file for testing
    with open('market_report.html', 'w') as f:
        f.write(email_content)
    print("\nReport saved to market_report.html")


if __name__ == "__main__":
    asyncio.run(main())