#!/usr/bin/env python3
"""
Main script to run the market research agent
Can be executed manually or via GitHub Actions
"""

import asyncio
import sys
from datetime import datetime
from market_research_agent import MarketResearchAgent
from email_sender import EmailSender
from slack_sender import SlackSender
import os


async def main():
    """Run the complete market research workflow"""
    print(f"\n{'='*50}")
    print(f"Market Research Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    try:
        # Initialize agent
        agent = MarketResearchAgent()
        
        # Collect and analyze market data
        print("Starting market analysis...")
        analysis = await agent.analyze_market()
        print(f"\n{analysis}\n")
        
        # --- Notifications --- #
        print("Sending notifications...")
        email_content = agent.format_email_content(analysis)  # Convert to beautifully formatted HTML
        email_sender = EmailSender()
        subject = "Daily Market Research Report"
        if email_sender.send(subject, email_content):
            print("✓ Email sent successfully")
        else:
            print("✗ Failed to send email")
        
        # Send to Slack (if configured)
        slack_sender = SlackSender()
        if os.getenv("SLACK_BOT_TOKEN"):
            if slack_sender.send(analysis):
                print("✓ Slack message sent successfully")
            else:
                print("✗ Failed to send Slack message")
        else:
            print("ℹ Slack notification skipped (not configured)")
        
        # --- Save Report --- #
        # report_filename = f"reports/market_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        # os.makedirs("reports", exist_ok=True)
        # with open(report_filename, "w") as f:
        #     # Wrap the plain text in a <pre> tag for HTML formatting
        #     html_content = f"<html><body><pre>{analysis}</pre></body></html>"
        #     f.write(html_content)
        # print(f"✓ Report saved to {report_filename}")
        
        print(f"\n{'='*50}")
        print("Market research completed successfully!")
        print(f"{'='*50}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error running market research: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)