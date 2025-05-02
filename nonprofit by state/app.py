from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import glob
import traceback
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    """Clean and normalize text for searching"""
    if pd.isna(text):
        return ''
    return str(text).lower().strip()

def search_in_text(text, query):
    """Search for query phrase within the text."""
    if not text or pd.isna(text):
        return False
    # Clean both text and query for consistent comparison
    cleaned_text = str(text).lower().strip()
    cleaned_query = query.lower().strip()
    return cleaned_query in cleaned_text

# Load all CSV files into memory
def load_data():
    data = {}
    
    # First load international data
    try:
        logger.info("Loading international nonprofits data...")
        # Try both possible international file names
        intl_files = ['international_nonprofits.csv', 'nonprofits_International_websites.csv']
        intl_df = None
        for file in intl_files:
            if os.path.exists(file):
                logger.info(f"Attempting to load {file}...")
                try:
                    intl_df = pd.read_csv(file)
                    # Ensure consistent column names
                    if 'URL' in intl_df.columns:
                        intl_df = intl_df.rename(columns={'URL': 'Website'})
                    # Add missing columns if necessary
                    if 'Country' not in intl_df.columns:
                        intl_df['Country'] = 'International'
                    if 'State' not in intl_df.columns:
                        intl_df['State'] = ''
                    if 'City' not in intl_df.columns:
                        intl_df['City'] = ''
                    if 'PC' not in intl_df.columns:
                        intl_df['PC'] = 'FORGN'
                    
                    logger.info(f"Successfully loaded {file} with {len(intl_df)} records")
                    logger.info(f"Columns in {file}: {list(intl_df.columns)}")
                    break
                except Exception as e:
                    logger.error(f"Error loading {file}: {e}")
                    continue
        
        if intl_df is not None:
            # Convert all string columns to lowercase for case-insensitive search
            for col in intl_df.select_dtypes(include=['object']).columns:
                intl_df[col] = intl_df[col].apply(clean_text)
            data['INT'] = intl_df
            logger.info(f"Loaded international data with {len(intl_df)} records")
        else:
            logger.warning("No international nonprofits file found")
    except Exception as e:
        logger.error(f"Error loading international data: {e}")
        logger.error(traceback.format_exc())
    
    # Then load state and territory files (both CSV and TXT)
    csv_files = glob.glob('nonprofits_*.csv')
    txt_files = glob.glob('nonprofits_*.txt')
    all_files = csv_files + txt_files
    logger.info(f"Found {len(all_files)} files to process ({len(csv_files)} CSV, {len(txt_files)} TXT)")
    
    for file in all_files:
        # Skip only the empty state file
        if file == 'nonprofits_.csv' or file == 'nonprofits_.txt':
            logger.info(f"Skipping file: {file}")
            continue
            
        state_code = file.split('_')[1].split('.')[0]
        try:
            logger.info(f"Loading {state_code} data from {file}...")
            # Handle both CSV and TXT files
            if file.endswith('.csv'):
                df = pd.read_csv(file)
            else:  # TXT file
                # Read TXT file with appropriate delimiter
                df = pd.read_csv(file, delimiter='|', header=None)
                # Add column names if needed
                if len(df.columns) >= 6:  # Assuming standard format
                    df.columns = ['EIN', 'Organization Name', 'City', 'State', 'Country', 'PC']
                    if len(df.columns) > 6:
                        df['Website'] = df.iloc[:, 6]
            
            if 'URL' in df.columns:
                df = df.rename(columns={'URL': 'Website'})
            # Convert all string columns to lowercase for case-insensitive search
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(clean_text)
            data[state_code] = df
            logger.info(f"Loaded {state_code} data with {len(df)} records")
        except Exception as e:
            logger.error(f"Error loading {file}: {e}")
            logger.error(traceback.format_exc())
    
    logger.info(f"Successfully loaded data for {len(data)} locations")
    return data

# Load data at startup
logger.info("Starting application...")
nonprofit_data = load_data()
logger.info("Data loading complete")

@app.route('/')
def index():
    # Get list of available states/territories for the dropdown
    states = sorted([code for code in nonprofit_data.keys() if code != 'INT'])
    return render_template('index.html', states=states)

@app.route('/search', methods=['GET'])
def search():
    try:
        query = request.args.get('q', '').lower().strip()
        state = request.args.get('state', '').upper()
        international_only = request.args.get('international_only', 'false').lower() == 'true'
        
        logger.info(f"Search request - Query: '{query}', State: '{state}', International Only: {international_only}")
        
        if not query:
            logger.info("Empty query received, returning empty results")
            return jsonify([])
            
        results = []
        
        # If state is INT or international_only is true, only search international data
        if state == 'INT' or international_only:
            if 'INT' in nonprofit_data:
                df = nonprofit_data['INT']
                # Search across all columns
                mask = pd.Series(False, index=df.index)
                for col in df.columns:
                    mask |= df[col].apply(lambda x: search_in_text(x, query))
                
                results = df[mask].to_dict('records')
                logger.info(f"Found {len(results)} international results")
            else:
                logger.warning("No international data available")
        # If state is specified, only search that state's data
        elif state:
            if state in nonprofit_data:
                df = nonprofit_data[state]
                # Search across all columns
                mask = pd.Series(False, index=df.index)
                for col in df.columns:
                    mask |= df[col].apply(lambda x: search_in_text(x, query))
                
                results = df[mask].to_dict('records')
                logger.info(f"Found {len(results)} results in state {state}")
            else:
                logger.warning(f"State {state} not found in data")
        else:
            # Search all states and international data
            for state_code, df in nonprofit_data.items():
                # Search across all columns
                mask = pd.Series(False, index=df.index)
                for col in df.columns:
                    mask |= df[col].apply(lambda x: search_in_text(x, query))
                
                state_results = df[mask].to_dict('records')
                results.extend(state_results)
                logger.info(f"Found {len(state_results)} results in {state_code}")
        
        # Sort results by relevance
        def get_sort_key(x):
            # Calculate relevance score based on number of matches and field importance
            score = 0
            query_words = query.split()
            
            # Special handling for international organizations
            is_international = x.get('Country', '').lower() != 'united states'
            
            # Organization name matches are most important
            org_name = clean_text(x.get('Organization Name', ''))
            if org_name:
                score += sum(1 for word in query_words if word in org_name) * (4 if is_international else 3)
            
            # Country matches are second most important
            country = clean_text(x.get('Country', ''))
            if country:
                score += sum(1 for word in query_words if word in country) * (3 if is_international else 2)
            
            # City and State matches are third most important
            city = clean_text(x.get('City', ''))
            state_val = clean_text(x.get('State', ''))
            if city:
                score += sum(1 for word in query_words if word in city) * (2 if is_international else 1)
            if state_val:
                score += sum(1 for word in query_words if word in state_val)
            
            # Other fields contribute to the score
            for key, value in x.items():
                if key not in ['Organization Name', 'Country', 'City', 'State']:
                    text = clean_text(value)
                    if text:
                        score += sum(1 for word in query_words if word in text) * (1 if is_international else 0.5)
            
            return score
        
        results.sort(key=get_sort_key, reverse=True)
        
        # Convert back to original case for display
        for result in results:
            for key in result:
                if isinstance(result[key], str):
                    result[key] = result[key].title()
        
        logger.info(f"Total results found: {len(results)}")
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error in search: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 