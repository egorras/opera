import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from notion_shows_handler import NotionShowsHandler

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
        
    def format_url(self, year, month):
        """Format the URL by inserting year and month."""
        return self.base_url.format(year=year, month=month)

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
        for post in soup.findAll('article', class_='post'):
            event_data = {
                'id': post.get('data-ksys-id'),
                'title': post.find('a', class_='post-title-link').contents[0].strip(),
                'is_rehearsal': post.find('span', class_='tag tag--premier', text='rehearsal') is not None,
                'show_url': self.base_url + '/'.join(post.find('h2', class_='post-title').a.get('href').split('/')[:-1]),
                'tags': [tag.contents[0].strip() for tag in post.find_all('span', class_='tag')]
            }
            self.notion_shows_handler.try_push_show_to_notion(event_data)
            logging.info(event_data)
