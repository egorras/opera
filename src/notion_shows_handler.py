import os
from notion_client import Client
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NotionShowsHandler:
    def __init__(self):
        self.notion = Client(auth=os.getenv('NOTION_API_KEY'))
        self.database_id = os.getenv('NOTION_SHOWS_DATABASE_ID')
        self.valid_tags = ['opera', 'contemporary', 'ballet']

    def item_exists(self, item_id):
        """Check if an item with the same id already exists in the Notion database."""
        query = self.notion.databases.query(
            **{
                "database_id": self.database_id,
                "filter": {
                    "property": "Id",
                    "rich_text": {
                        "equals": item_id
                    }
                }
            }
        )
        return len(query['results']) > 0

    def try_push_show_to_notion(self, event):
        # Skip rehearsal as it comes first and has a different name
        if event['is_rehearsal']:
            logging.info(f"Event '{event['title']}' is rehearsal.")
            return

        """Push show to Notion if it doesn't already exist."""
        if not self.item_exists(event['id']):
            self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Id": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": event['id']
                                }
                            }
                        ]
                    },
                    "Title": {
                        "title": [
                            {
                                "text": {
                                    "content": event['title']
                                }
                            }
                        ]
                    },
                    "Tags": {
                        "multi_select": [{"name": tag} for tag in [tag for tag in event['tags'] if tag in self.valid_tags]]
                    },
                    "Show URL": {"url": event['show_url']}
                }
            )
            logging.info(f"Event '{event['title']}' added to Notion.")
        else:
            logging.info(f"Event '{event['title']}' already exists in Notion.")
