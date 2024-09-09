import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from notion_shows_handler import NotionShowsHandler
from datetime import datetime
import pytz

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OperaCrawler:
    def __init__(self):
        self.notion_shows_handler = NotionShowsHandler()
        self.base_url = os.getenv('BASE_URL')
        if not self.base_url:
            raise ValueError("BASE_URL is not set in the environment variables.")
        self.tz = pytz.timezone('Europe/Budapest')
        
    def format_url(self, year, month):
        """Format the URL by inserting year and month."""
        return f"{self.base_url}/en/programme/?y={year}&m={month}"

    def fetch_page(self, url):
        """Fetch the page content from the URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch URL: {url} due to {e}")
            return None

    def has_content(self, html_content):
        """Check if the page contains events."""
        soup = BeautifulSoup(html_content, 'html.parser')
        event_list = soup.find_all(class_='day')
        return len(event_list) > 0

    def crawl(self, start_year, start_month):
        """Iterate through pages and crawl events."""
        current_year = start_year
        current_month = start_month

        while True:
            url = self.format_url(current_year, current_month)
            logging.info(f"Checking URL: {url}")
            
            html_content = self.fetch_page(url)
            if html_content and self.has_content(html_content):
                logging.info(f"Content found for {current_year}-{current_month}")
                self.process_content(html_content)
            else:
                logging.info(f"No content found for {current_year}-{current_month}. Stopping.")
                break

            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1

    def process_content(self, html_content):
        """Process and extract event data."""
        logging.info("Processing event content...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        days = soup.find_all('li', class_='day')

        for day in days:
            # Extract the date from the ID (e.g., nap_20240906 -> 2024-09-06)
            day_id = day.get('id')  # e.g., 'nap_20240906'
            event_date = f"{day_id[4:8]}-{day_id[8:10]}-{day_id[10:12]}"  # Convert to YYYY-MM-DD

            # Find all events for that day
            for post in day.find_all('article', class_='post'):
                
                time_text = post.find('div', class_='post-time').contents[0].strip()
                event_datetime_str = f"{event_date} {time_text}"  # Combine date and time (e.g., "2024-09-06 18:00")
                event_datetime = self.tz.localize(datetime.strptime(event_datetime_str, "%Y-%m-%d %H:%M"))
                event_datetime_utc = event_datetime.astimezone(pytz.utc).isoformat()

                # Extract the duration in minutes
                duration_in_minutes = 0
                duration_text = post.find('div', class_='post-length')
                if duration_text and len(duration_text.contents) > 0:
                    duration_in_minutes = int(duration_text.contents[0].split()[0])  # Extract the number part

                event_data = {
                    'id': post.get('data-ksys-id'),
                    'title': post.find('a', class_='post-title-link').contents[0].strip(),
                    'is_rehearsal': post.find('span', class_='tag tag--premier', text='rehearsal') is not None,
                    'show_url': self.base_url + post.find('h2', class_='post-title').a.get('href'),
                    'tags': [tag.contents[0].strip() for tag in post.find_all('span', class_='tag')],
                    'location': post.find('span', class_='post-location-name').contents[0].strip(),
                    'duration': duration_in_minutes,
                    'date': event_datetime_utc,
                    'date_str': event_datetime_str
                }
                self.notion_shows_handler.push_event_to_notion(event_data)
                logging.info(event_data)
