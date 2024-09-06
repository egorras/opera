from datetime import datetime
from opera_crawler import OperaCrawler

def main():
    # Initialize the main services
    opera_crawler = OperaCrawler()
    
    # Start the crawler from the current month and year
    now = datetime.now()
    opera_crawler.crawl(now.year, now.month)

if __name__ == "__main__":
    main()
