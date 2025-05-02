import csv
import time
import os
import sys
import re
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, parse_qs

# List of user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.78',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def clean_url(url):
    """Clean tracking parameters from URLs and get the base domain."""
    if not url:
        return ""
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Extract just the scheme and netloc (domain) parts
    # For example, from https://www.example.com/path?query=param
    # we get https://www.example.com
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # If there's a path, add it, but limit to first directory level
    if parsed.path:
        path_parts = parsed.path.split('/')
        if len(path_parts) > 1:
            base_url += f"/{path_parts[1]}"
    
    return base_url

def search_organization_website(org_name, state="Iowa", max_retries=3):
    """Search for an organization's website using DuckDuckGo with retry mechanism."""
    for attempt in range(max_retries):
        try:
            # Format the search query
            query = f"{org_name} {state} nonprofit official website"
            encoded_query = quote_plus(query)
            
            # Create the DuckDuckGo search URL
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Add headers to mimic a browser request - use random user agent
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://duckduckgo.com/'
            }
            
            # Make the request
            response = requests.get(url, headers=headers)
            
            if response.status_code == 202:
                print(f"Received 202 status for {org_name} - Attempt {attempt+1}/{max_retries}")
                # Longer wait for 202 status
                retry_delay = random.uniform(20, 30)
                print(f"Waiting {retry_delay:.2f} seconds before retry...")
                time.sleep(retry_delay)
                continue
                
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code} for {org_name}")
                return ""
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all result URLs
            results = soup.find_all('a', class_='result__url')
            
            # List of domains to exclude
            excluded_domains = [
                'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
                'guidestar.org', 'charity', 'irs.gov', 'wikipedia.org', 'youtube.com',
                'charitynavigator.org', 'propublica.org', 'candid.org', 'cause', 'charity',
                'pinterest', '990finder', 'greatnonprofits', 'nonprofitfacts', 
                'faqs.org', 'nccsweb', 'amazonaws', 'taxexemptworld', 'duckduckgo.com'
            ]
            
            if results:
                for result in results:
                    # Get the URL text
                    website = result.get('href')
                    
                    # Skip empty urls
                    if not website:
                        continue
                    
                    # Clean the URL to remove tracking parameters
                    clean_website = clean_url(website)
                    
                    # Skip excluded domains
                    if any(domain in clean_website.lower() for domain in excluded_domains):
                        continue
                    
                    # If we made it here, return this URL
                    return clean_website
            
            # If no suitable results found, return empty string
            return ""
            
        except Exception as e:
            print(f"Error searching for {org_name}: {e}")
            if attempt < max_retries - 1:
                retry_delay = random.uniform(15, 25)
                print(f"Retrying in {retry_delay:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                return ""

def main():
    print("Script starting...")
    print(f"Current directory: {os.getcwd()}")
    
    # Set the input and output file paths
    input_file = "nonprofits_IA.csv"
    output_file = "nonprofits_IA_with_websites.csv"
    
    # Read the input CSV file
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header = next(reader)  # Get the header row
        data = list(reader)  # Get all the data rows
    
    print(f"Successfully read {len(data)} rows from the input file.")
    
    # Add the "Website" column to the header if not already there
    if "Website" not in header:
        header.append('Website')
    
    # Check if output file exists and find the last processed row
    resume_from_row = 0
    if os.path.exists(output_file):
        with open(output_file, 'r', newline='', encoding='utf-8') as outfile:
            output_reader = csv.reader(outfile)
            output_header = next(output_reader)
            output_data = list(output_reader)
            
            # Find the last row that has a website
            for i, row in enumerate(output_data):
                if len(row) > len(header) - 1 and row[len(header) - 1]:
                    resume_from_row = i + 1
            
            # If we found a partially processed file, use its data
            if output_data:
                data = output_data
                print(f"Found existing output file. Resuming from row {resume_from_row}")
    
    # Process each row and find the website
    max_rows = len(data)  # Process all rows by default
    
    start_row = resume_from_row
    end_row = min(start_row + max_rows, len(data))
    
    print(f"Processing rows {start_row} to {end_row-1} (total: {end_row-start_row} organizations)")
    print("Using randomized delays between requests to avoid rate limiting")
    
    try:
        for i in range(start_row, end_row):
            row = data[i]
            
            # Skip rows that already have a website
            if len(row) > len(header) - 1 and row[len(header) - 1]:
                continue
                
            if len(row) >= 2:  # Make sure we have at least the organization name
                org_name = row[1]  # Organization Name is in the second column
                
                print(f"Processing {i+1}/{end_row}: {org_name}")
                
                # Search for the website
                website = search_organization_website(org_name)
                
                # Ensure the row has enough elements
                while len(row) < len(header) - 1:
                    row.append("")
                
                # Add website or update if already exists
                if len(row) < len(header):
                    row.append(website)
                else:
                    row[len(header) - 1] = website
                
                print(f"Found website: {website}")
                
                # Save progress every 5 organizations
                if (i - start_row + 1) % 5 == 0:
                    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
                        writer = csv.writer(outfile)
                        writer.writerow(header)  # Write the header row
                        writer.writerows(data)   # Write the data rows
                    print(f"Progress saved at row {i+1}")
                
                # Add a randomized delay to avoid rate limiting
                # Random delay between 8 and 15 seconds
                delay = random.uniform(8, 15)
                print(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
                
                # Occasionally add a longer pause (25% chance)
                if random.random() < 0.25:
                    long_delay = random.uniform(25, 40)
                    print(f"Taking a longer break: {long_delay:.2f} seconds...")
                    time.sleep(long_delay)
    
    except KeyboardInterrupt:
        print("Process interrupted by user. Saving progress...")
    finally:
        # Write the output CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)  # Write the header row
            writer.writerows(data)   # Write the data rows
        
        print(f"Completed processing. Results saved to {output_file}")

if __name__ == "__main__":
    main() 