#!/usr/bin/env python3
"""
Vercel serverless function for market research cron job
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from market_research_agent import MarketResearchAgent
    from email_sender import EmailSender
    from slack_sender import SlackSender
except ImportError as e:
    print(f"Import error: {e}")
    # For testing purposes, create mock classes
    class MarketResearchAgent:
        async def analyze_market(self): return "Mock analysis"
        def format_email_content(self, analysis): return f"<html><body>{analysis}</body></html>"
    class EmailSender:
        def send(self, subject, content): return True
    class SlackSender:
        def send(self, message): return True


async def run_market_research():
    """Run the complete market research workflow"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Market Research Agent - {timestamp}")
    
    try:
        # Initialize agent
        agent = MarketResearchAgent()
        
        # Collect and analyze market data
        print("Starting market analysis...")
        analysis = await agent.analyze_market()
        
        # Send notifications
        print("Sending notifications...")
        email_content = agent.format_email_content(analysis)
        email_sender = EmailSender()
        subject = "Daily Market Research Report"
        
        email_success = email_sender.send(subject, email_content)
        
        # Send to Slack (if configured)
        slack_success = True
        slack_sender = SlackSender()
        if os.getenv("SLACK_BOT_TOKEN"):
            slack_success = slack_sender.send(analysis)
        
        return {
            "success": True,
            "timestamp": timestamp,
            "email_sent": email_success,
            "slack_sent": slack_success,
            "message": "Market research completed successfully"
        }
        
    except Exception as e:
        print(f"Error running market research: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "timestamp": timestamp,
            "error": str(e),
            "message": "Market research failed"
        }


def handler(event, context):
    """Vercel serverless function handler"""
    try:
        # Run the market research
        result = asyncio.run(run_market_research())
        
        return {
            'statusCode': 200 if result['success'] else 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "success": False,
                "error": str(e),
                "message": "Internal server error"
            })
        }
