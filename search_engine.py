import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
from pathlib import Path
import streamlit as st
import chardet
import urllib.parse
import torch

class NonprofitSearchEngine:
    def __init__(self):
        # Initialize the model without device specification
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Force CPU usage
        self.model.to('cpu')
        # Disable gradient computation
        torch.set_grad_enabled(False)
        self.data = None
        self.index = None
        self.embeddings = None
        self.vector_dim = 384  # Dimension of the embeddings
        
    def detect_encoding(self, file_path):
        """Detect the encoding of a file"""
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        return result['encoding']
        
    def load_data(self):
        """Load and combine data from all CSV files in the directories"""
        dfs = []
        
        # Load international nonprofits data
        intl_path = Path("international nonprofits")
        if (intl_path / "international_nonprofits_with_emails.csv").exists():
            file_path = intl_path / "international_nonprofits_with_emails.csv"
            encoding = self.detect_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding)
            dfs.append(df)
        
        # Load IA nonprofits data
        # ia_path = Path("IA nonprofits")
        # for csv_file in ia_path.glob("*.csv"):
        #     encoding = self.detect_encoding(csv_file)
        #     df = pd.read_csv(csv_file, encoding=encoding)
        #     dfs.append(df)
            
        # Combine all dataframes
        if dfs:
            self.data = pd.concat(dfs, ignore_index=True)
            # Clean and prepare data
            self.data = self.data.fillna('')
            # Remove duplicates based on EIN
            self.data = self.data.drop_duplicates(subset=['EIN'], keep='first')
            # Create a searchable text field
            self.data['search_text'] = self.data.apply(
                lambda row: f"{row['Organization Name']} {row['City']} {row['State']} {row['Country']} {row['Website']} {row['Email Addresses']}",
                axis=1
            )
        else:
            raise ValueError("No CSV files found in the specified directories")
    
    def build_index(self):
        """Create embeddings and build FAISS index"""
        if self.data is None:
            self.load_data()
            
        # Create embeddings for all searchable text
        self.embeddings = self.model.encode(self.data['search_text'].tolist())
        
        # Create and train FAISS index
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.index.add(self.embeddings.astype('float32'))
    
    def search(self, query, k=10):
        """Search for nonprofits based on query"""
        if self.index is None:
            self.build_index()
            
        # Create embedding for query
        query_embedding = self.model.encode([query])
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Get results
        results = self.data.iloc[indices[0]].copy()
        results['similarity_score'] = 1 / (1 + distances[0])  # Convert distance to similarity score
        
        return results

def main():
    # Add Jotform bot script
    st.markdown("""
    <script src='https://cdn.jotfor.ms/s/umd/latest/for-embedded-agent.js'></script>
    <script>
      window.addEventListener("DOMContentLoaded", function() {
        window.AgentInitializer.init({
          agentRenderURL: "https://agent.jotform.com/01952a9d3fb275588d4fce8dc19d1aa9d6e0/voice",
          rootId: "JotformAgent-01952a9d3fb275588d4fce8dc19d1aa9d6e0",
          formID: "01952a9d3fb275588d4fce8dc19d1aa9d6e0",
          queryParams: ["skipWelcome=1", "maximizable=1"],
          domain: "https://www.jotform.com",
          isDraggable: false,
          background: "linear-gradient(180deg, #D3CBF4 0%, #D3CBF4 100%)",
          buttonBackgroundColor: "#8797FF",
          buttonIconColor: "#01091B",
          variant: false,
          customizations: {
            "greeting": "Yes",
            "greetingMessage": "Hi! How can I assist you?",
            "openByDefault": "No",
            "pulse": "Yes",
            "position": "right",
            "autoOpenChatIn": "0"
          },
          isVoice: true,
        });
      });
    </script>
    """, unsafe_allow_html=True)
    
    st.title("Nonprofit Search Engine")
    
    # Initialize search engine
    if 'search_engine' not in st.session_state:
        st.session_state.search_engine = NonprofitSearchEngine()
        with st.spinner('Loading data and building search index...'):
            st.session_state.search_engine.load_data()
            st.session_state.search_engine.build_index()
    
    # Search interface
    query = st.text_input("Search for nonprofits:", "")
    
    # Display results
    if query:
        results = st.session_state.search_engine.search(query)
        
        # Display results
        for _, row in results.iterrows():
            with st.expander(f"{row['Organization Name']} (Score: {row['similarity_score']:.2f})"):
                st.write(f"**EIN:** {row['EIN']}")
                st.write(f"**Location:** {row['City']}, {row['State']}, {row['Country']}")
                if row['Website']:
                    st.write(f"**Website:** {row['Website']}")
                if row['Email Addresses']:
                    st.write(f"**Email:** {row['Email Addresses']}")
                
                # Add subtle Google search link
                search_query = f"{row['Organization Name']} {row['City']} {row['State']} {row['Country']}"
                google_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
                st.markdown(f'<div style="margin-top: 10px; font-size: 0.9em; color: #666;"><a href="{google_url}" target="_blank">🔍 Search on Google</a></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 