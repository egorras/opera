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
        self.repertoire_database_id = os.getenv('NOTION_REPERTOIRE_DATABASE_ID')
        self.events_database_id = os.getenv('NOTION_EVENTS_DATABASE_ID')
        self.valid_tags = ['opera', 'contemporary', 'ballet', 'mixed', 'concert']
        self.repertoire_cache = {}

    def repertoire_exists(self, item_id):
        if item_id in self.repertoire_cache:
            return self.repertoire_cache[item_id]

        """Check if an item with the same id already exists in the Notion database."""
        query = self.notion.databases.query(
            **{
                "database_id": self.repertoire_database_id,
                "filter": {
                    "property": "Id",
                    "rich_text": {
                        "equals": item_id
                    }
                }
            }
        )
        if len(query['results']) > 0:
            repertoire_id = query['results'][0]['id']
            # Add to cache
            self.repertoire_cache[item_id] = repertoire_id
            return repertoire_id
        return None
    
    def event_exists(self, event_date, repertoire_id):
        """Check if an event already exists in the Events database."""
        query = self.notion.databases.query(
            **{
                "database_id": self.events_database_id,
                "filter": {
                    "and": [
                        {
                            "property": "Time",
                            "date": {
                                "equals": event_date
                            }
                        },
                        {
                            "property": "Repertoire",
                            "relation": {
                                "contains": repertoire_id
                            }
                        }
                    ]
                }
            }
        )
        return query['results'][0] if len(query['results']) > 0 else None

    def push_repertoire_to_notion(self, event):
        # Skip rehearsal as it comes first and has a different name
        # if event['is_rehearsal']:
        #     logging.info(f"Event '{event['title']}' is rehearsal.")
        #     return

        existing_repertoire = self.repertoire_exists(event['id'])

        """Push show to Notion if it doesn't already exist."""
        if existing_repertoire:
            logging.info(f"Event '{event['title']}' already exists in Notion.")
            return existing_repertoire

        new_repertoire = self.notion.pages.create(
            parent={"database_id": self.repertoire_database_id},
            properties={
                "Id": {"rich_text": [{"text": {"content": event['id']}}]},
                "Title": {"title": [{"text": {"content": event['title']}}]},
                "Tags": {"multi_select": [{"name": tag} for tag in [tag for tag in event['tags'] if tag in self.valid_tags]]},
                "Show URL": {"url": event['show_url']},
                "Venue": {"rich_text": [{"text": {"content": event['location']}}]},
                "Duraion (minutes)": {"number": event['duration']}
            }
        )
        logging.info(f"Event '{event['title']}' added to Notion.")
        return new_repertoire['id']

    def push_event_to_notion(self, event_data):
        """Push an event to the Notion Events database, with a relation to Repertoire."""
        # Get or create the related repertoire entry
        repertoire_id = self.push_repertoire_to_notion(event_data)

        # Check if the event already exists
        if not self.event_exists(event_data['date'], repertoire_id):
            # Create the event in the Events database
            self.notion.pages.create(
                parent={"database_id": self.events_database_id},
                properties={
                    "Repertoire": {"relation": [{"id": repertoire_id}]},
                    "Time": {"date": {"start": event_data['date']}},
                    "Date": {"title": [{"text": {"content": event_data['date_str']}}]},
                    "Event URL": {"url": event_data['show_url']}
                }
            )
            logging.info(f"Event '{event_data['date']}' added to Notion for repertoire: {event_data['title']}")
        else:
            logging.info(f"Event '{event_data['date']}' already exists in Notion.")
