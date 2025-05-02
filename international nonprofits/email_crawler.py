import csv
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging
from datetime import datetime
from urllib.parse import urlparse, urljoin
import os
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

class EmailCrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.delay_range = (2, 5)  # Random delay between 2-5 seconds
        self.found_emails = {}  # Dictionary to store emails by URL
        self.processed_urls = set()
        self.checkpoint_interval = 10  # Save results every 10 URLs
        self.output_file = 'international_nonprofits_with_emails.csv'
        
    def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(*self.delay_range)
        logging.info(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
        
    def get_random_headers(self):
        """Generate random headers for requests"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
            
    def extract_emails_from_text(self, text):
        """Extract email addresses from text"""
        # First try to find emails in mailto: links
        mailto_emails = set()
        soup = BeautifulSoup(text, 'html.parser')
        for link in soup.find_all('a', href=True):
            if link['href'].startswith('mailto:'):
                email = link['href'][7:]  # Remove 'mailto:' prefix
                if re.match(self.email_pattern, email):
                    mailto_emails.add(email)
        
        # Then find emails in the text
        text_emails = set(re.findall(self.email_pattern, text))
        
        # Combine and return all found emails
        all_emails = mailto_emails.union(text_emails)
        if all_emails:
            logging.info(f"Found {len(all_emails)} email(s): {', '.join(all_emails)}")
        return all_emails
        
    def is_valid_url(self, url):
        """Check if the URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    def get_page_content(self, url):
        """Get page content with error handling"""
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch {url}: {str(e)}")
            return None
            
    def find_contact_links(self, soup, base_url):
        """Find contact-related links in the page"""
        contact_keywords = ['contact', 'about', 'connect', 'reach', 'get in touch', 'email', 'mail']
        contact_links = set()
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            # Check if link text or URL contains contact-related keywords
            if any(keyword in href or keyword in text for keyword in contact_keywords):
                full_url = urljoin(base_url, link['href'])
                if self.is_valid_url(full_url):
                    contact_links.add(full_url)
                    logging.info(f"Found contact link: {full_url}")
                    
        return contact_links
            
    def process_url(self, url):
        """Process a single URL to find email addresses"""
        try:
            # Validate URL
            if not self.is_valid_url(url):
                logging.warning(f"Skipping invalid URL: {url}")
                return
                
            logging.info(f"Processing URL: {url}")
            
            # Get main page content
            main_content = self.get_page_content(url)
            if main_content:
                # Extract emails from main page
                emails = self.extract_emails_from_text(main_content)
                self.found_emails[url] = emails
                
                # Parse the page with BeautifulSoup
                soup = BeautifulSoup(main_content, 'html.parser')
                
                # Find and process contact links
                contact_links = self.find_contact_links(soup, url)
                for contact_url in contact_links:
                    contact_content = self.get_page_content(contact_url)
                    if contact_content:
                        contact_emails = self.extract_emails_from_text(contact_content)
                        self.found_emails[url].update(contact_emails)
                        self.random_delay()
                    
            self.processed_urls.add(url)
            self.random_delay()
            
        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")
            
    def save_results(self):
        """Save results to a copy of the original CSV with an additional email column"""
        # Create a backup of the original file if it doesn't exist
        if not os.path.exists('international_nonprofits_backup.csv'):
            shutil.copy2('international_nonprofits.csv', 'international_nonprofits_backup.csv')
            
        # Read the original CSV and create a new one with the email column
        with open('international_nonprofits.csv', 'r', newline='') as infile, \
             open(self.output_file, 'w', newline='') as outfile:
            
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # Read and write header row
            header = next(reader)
            header.append('Email Addresses')  # Add email column
            writer.writerow(header)
            
            # Process each row
            for row in reader:
                if row and row[-1].strip():  # Check if there's a URL
                    url = row[-1].strip()
                    if not url.startswith(('http://', 'https://')) and '.' in url:
                        url = 'https://' + url
                    
                    # Get emails for this URL
                    emails = self.found_emails.get(url, set())
                    row.append(','.join(sorted(emails)))  # Add emails as comma-separated string
                else:
                    row.append('')  # Add empty email field if no URL
                
                writer.writerow(row)
                
        logging.info(f"Saved results to {self.output_file}")
                
    def load_checkpoint(self):
        """Load previously found emails and processed URLs"""
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                email_col_index = header.index('Email Addresses')
                
                for row in reader:
                    if row and row[-2].strip():  # Check URL column (second to last)
                        url = row[-2].strip()
                        if not url.startswith(('http://', 'https://')) and '.' in url:
                            url = 'https://' + url
                        emails = set(row[email_col_index].split(',')) if row[email_col_index] else set()
                        self.found_emails[url] = emails
                        self.processed_urls.add(url)
                        
            logging.info(f"Loaded {len(self.found_emails)} previously processed URLs with emails")
                
def main():
    crawler = EmailCrawler()
    
    # Try to load previous results
    crawler.load_checkpoint()
    
    # Read URLs from the source file
    try:
        with open('international_nonprofits.csv', 'r', newline='') as f:
            reader = csv.reader(f)
            # Skip header row if it exists
            next(reader, None)
            # Get URLs from the last column and filter out invalid ones
            urls = []
            for row in reader:
                if row and row[-1].strip():
                    url = row[-1].strip()
                    # Add https:// if no scheme is present and it looks like a domain
                    if not url.startswith(('http://', 'https://')) and '.' in url:
                        url = 'https://' + url
                    urls.append(url)
            
        logging.info(f"Found {len(urls)} URLs to process")
        
        # Process each URL
        for i, url in enumerate(urls, 1):
            if url not in crawler.processed_urls:  # Skip already processed URLs
                crawler.process_url(url)
                
                # Save results periodically
                if i % crawler.checkpoint_interval == 0:
                    crawler.save_results()
                    logging.info(f"Progress: {i}/{len(urls)} URLs processed")
            
        # Final save
        crawler.save_results()
        logging.info(f"Completed processing all URLs. Total unique emails found: {sum(len(emails) for emails in crawler.found_emails.values())}")
        
    except Exception as e:
        logging.error(f"Error in main process: {str(e)}")
        # Save results in case of error
        crawler.save_results()

if __name__ == "__main__":
    main() 