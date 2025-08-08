"""
Slack integration for market research reports
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()


class SlackSender:
    """Handles sending messages to Slack"""
    
    def __init__(self):
        self.client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        self.channel = os.getenv('SLACK_CHANNEL')

    def send(self, analysis: str) -> bool:
        """Sends the market analysis text to a Slack channel"""
        if not self.client.token or not self.channel:
            return False
        
        try:
            message_text = f"*Market Research Report - {datetime.now().strftime('%B %d, %Y')}*\n\n```{analysis}```"
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message_text,
                mrkdwn=True
            )
            return response.get('ok', False)
        except SlackApiError as e:
            print(f"Error sending Slack message: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Unexpected error sending Slack message: {e}")
            return False