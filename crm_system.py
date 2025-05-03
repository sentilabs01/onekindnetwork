import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import json
from pathlib import Path
import os
from search_engine import NonprofitSearchEngine
import chardet

class CRMSystem:
    def __init__(self):
        self.db_path = "crm_database.db"
        self.init_database()
        self.search_engine = NonprofitSearchEngine()
        self.search_engine.load_data()
        self.search_engine.build_index()
        self.csv_paths = {
            'international': Path("international nonprofits/international_nonprofits_with_emails.csv"),
            'ia': Path("IA nonprofits/ia_nonprofits.csv")
        }

    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create prospects table
        c.execute('''CREATE TABLE IF NOT EXISTS prospects
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     organization_name TEXT,
                     ein TEXT UNIQUE,
                     contact_name TEXT,
                     phone TEXT,
                     email TEXT,
                     city TEXT,
                     state TEXT,
                     country TEXT,
                     website TEXT,
                     current_systems TEXT,
                     social_media TEXT,
                     notes TEXT,
                     do_not_contact INTEGER DEFAULT 0,
                     removed INTEGER DEFAULT 0,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Create email campaigns table
        c.execute('''CREATE TABLE IF NOT EXISTS email_campaigns
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     prospect_id INTEGER,
                     email_subject TEXT,
                     email_content TEXT,
                     sent_date TIMESTAMP,
                     status TEXT,
                     response TEXT,
                     FOREIGN KEY (prospect_id) REFERENCES prospects(id))''')

        conn.commit()
        conn.close()

    def detect_encoding(self, file_path):
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        return result['encoding']

    def update_csv(self, data):
        """Update CSV files with new prospect data"""
        for csv_path in self.csv_paths.values():
            if csv_path.exists():
                try:
                    encoding = self.detect_encoding(csv_path)
                    df = pd.read_csv(csv_path, encoding=encoding)
                    mask = df['EIN'] == data['ein']
                    # Add new columns if they don't exist
                    for col in ['Contact Name', 'Phone', 'Current Systems', 'Social Media', 'Notes', 'Do Not Contact', 'Removed']:
                        if col not in df.columns:
                            df[col] = ''
                    if mask.any():
                        # Update existing row
                        df.loc[mask, 'Organization Name'] = data['organization_name']
                        df.loc[mask, 'City'] = data['city']
                        df.loc[mask, 'State'] = data['state']
                        df.loc[mask, 'Country'] = data['country']
                        df.loc[mask, 'Website'] = data['website']
                        df.loc[mask, 'Email Addresses'] = data['email']
                        df.loc[mask, 'Contact Name'] = data['contact_name']
                        df.loc[mask, 'Phone'] = data['phone']
                        df.loc[mask, 'Current Systems'] = json.dumps(data['current_systems'])
                        df.loc[mask, 'Social Media'] = json.dumps(data['social_media'])
                        df.loc[mask, 'Notes'] = data['notes']
                        df.loc[mask, 'Do Not Contact'] = int(data.get('do_not_contact', 0))
                        df.loc[mask, 'Removed'] = int(data.get('removed', 0))
                    else:
                        new_row = pd.DataFrame({
                            'EIN': [data['ein']],
                            'Organization Name': [data['organization_name']],
                            'City': [data['city']],
                            'State': [data['state']],
                            'Country': [data['country']],
                            'Website': [data['website']],
                            'Email Addresses': [data['email']],
                            'Contact Name': [data['contact_name']],
                            'Phone': [data['phone']],
                            'Current Systems': [json.dumps(data['current_systems'])],
                            'Social Media': [json.dumps(data['social_media'])],
                            'Notes': [data['notes']],
                            'Do Not Contact': [int(data.get('do_not_contact', 0))],
                            'Removed': [int(data.get('removed', 0))]
                        })
                        df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(csv_path, index=False, encoding=encoding)
                except Exception as e:
                    st.error(f"Error updating CSV file {csv_path}: {str(e)}")

    def add_prospect(self, data):
        """Add a new prospect to the database and update CSV files"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO prospects 
                        (organization_name, ein, contact_name, phone, email, 
                         city, state, country, website, current_systems, 
                         social_media, notes, do_not_contact, removed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (data['organization_name'], data['ein'], data['contact_name'],
                      data['phone'], data['email'], data['city'], data['state'],
                      data['country'], data['website'], json.dumps(data['current_systems']),
                      json.dumps(data['social_media']), data['notes'],
                      int(data.get('do_not_contact', 0)), int(data.get('removed', 0))))
            conn.commit()
            self.update_csv(data)
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_prospect(self, prospect_id, data):
        """Update prospect information in database and CSV files"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''UPDATE prospects 
                        SET organization_name=?, contact_name=?, phone=?, email=?,
                            city=?, state=?, country=?, website=?, current_systems=?,
                            social_media=?, notes=?, do_not_contact=?, removed=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?''',
                     (data['organization_name'], data['contact_name'], data['phone'],
                      data['email'], data['city'], data['state'], data['country'],
                      data['website'], json.dumps(data['current_systems']),
                      json.dumps(data['social_media']), data['notes'],
                      int(data.get('do_not_contact', 0)), int(data.get('removed', 0)), prospect_id))
            conn.commit()
            self.update_csv(data)
            return True
        except Exception as e:
            st.error(f"Error updating prospect: {str(e)}")
            return False
        finally:
            conn.close()

    def add_email_campaign(self, prospect_id, subject, content):
        """Add a new email campaign entry"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO email_campaigns 
                    (prospect_id, email_subject, email_content, sent_date, status)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'Sent')''',
                 (prospect_id, subject, content))
        
        conn.commit()
        conn.close()

    def get_prospects(self, include_removed=False):
        """Get all prospects, optionally including removed ones"""
        conn = sqlite3.connect(self.db_path)
        if include_removed:
            df = pd.read_sql_query("SELECT * FROM prospects", conn)
        else:
            df = pd.read_sql_query("SELECT * FROM prospects WHERE removed=0", conn)
        conn.close()
        return df

    def get_email_campaigns(self, prospect_id=None):
        """Get email campaigns, optionally filtered by prospect"""
        conn = sqlite3.connect(self.db_path)
        if prospect_id:
            df = pd.read_sql_query(
                "SELECT * FROM email_campaigns WHERE prospect_id = ?", 
                conn, params=[prospect_id]
            )
        else:
            df = pd.read_sql_query("SELECT * FROM email_campaigns", conn)
        conn.close()
        return df

    def delete_prospect(self, ein):
        """Permanently delete a prospect from both the database and CSV by EIN"""
        # Delete from DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM prospects WHERE ein=?", (ein,))
        conn.commit()
        conn.close()
        # Delete from CSVs
        for csv_path in self.csv_paths.values():
            if csv_path.exists():
                try:
                    encoding = self.detect_encoding(csv_path)
                    df = pd.read_csv(csv_path, encoding=encoding)
                    df = df[df['EIN'] != ein]
                    df.to_csv(csv_path, index=False, encoding=encoding)
                except Exception as e:
                    st.error(f"Error deleting from CSV file {csv_path}: {str(e)}")

def main():
    st.set_page_config(page_title="One Kind Network CRM", layout="wide")
    
    # Initialize CRM system
    if 'crm' not in st.session_state:
        st.session_state.crm = CRMSystem()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Search Prospects", "Add Prospect", "View Prospects"])

    if page == "Search Prospects":
        st.title("Search Prospects")
        query = st.text_input("Search for prospects:", "")
        
        if query:
            results = st.session_state.crm.search_engine.search(query)
            
            for idx, row in results.iterrows():
                with st.expander(f"{row['Organization Name']} (Score: {row['similarity_score']:.2f})"):
                    st.write(f"**EIN:** {row['EIN']}")
                    st.write(f"**Location:** {row['City']}, {row['State']}, {row['Country']}")
                    if row['Website']:
                        st.write(f"**Website:** {row['Website']}")
                    if row['Email Addresses']:
                        st.write(f"**Email:** {row['Email Addresses']}")
                    dnc = st.checkbox("Do Not Contact", key=f"dnc_{row['EIN']}_{idx}")
                    if st.button("Add to CRM", key=f"add_{row['EIN']}"):
                        if dnc:
                            st.session_state.crm.delete_prospect(row['EIN'])
                            st.success("Prospect permanently deleted as DNC (Do Not Contact compliance).")
                            st.rerun()
                        else:
                            prospect_data = {
                                'organization_name': row['Organization Name'],
                                'ein': row['EIN'],
                                'contact_name': '',
                                'phone': '',
                                'email': row['Email Addresses'],
                                'city': row['City'],
                                'state': row['State'],
                                'country': row['Country'],
                                'website': row['Website'],
                                'current_systems': [],
                                'social_media': {},
                                'notes': '',
                                'do_not_contact': 0,
                                'removed': 0
                            }
                            if st.session_state.crm.add_prospect(prospect_data):
                                st.success("Prospect added to CRM!")
                            else:
                                st.error("Prospect already exists in CRM!")

    elif page == "Add Prospect":
        st.title("Add New Prospect")
        with st.form("add_prospect_form"):
            col1, col2 = st.columns(2)
            with col1:
                organization_name = st.text_input("Organization Name")
                ein = st.text_input("EIN")
                contact_name = st.text_input("Contact Name")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
            with col2:
                city = st.text_input("City")
                state = st.text_input("State")
                country = st.text_input("Country")
                website = st.text_input("Website")
            current_systems = st.multiselect(
                "Current Systems",
                ["CRM", "ERP", "Accounting", "HR", "Project Management", "Other"]
            )
            social_media = {}
            st.subheader("Social Media")
            col1, col2 = st.columns(2)
            with col1:
                social_media['linkedin'] = st.text_input("LinkedIn")
                social_media['twitter'] = st.text_input("Twitter")
            with col2:
                social_media['facebook'] = st.text_input("Facebook")
                social_media['instagram'] = st.text_input("Instagram")
            notes = st.text_area("Notes")
            do_not_contact = st.checkbox("Do Not Contact")
            if st.form_submit_button("Add Prospect"):
                prospect_data = {
                    'organization_name': organization_name,
                    'ein': ein,
                    'contact_name': contact_name,
                    'phone': phone,
                    'email': email,
                    'city': city,
                    'state': state,
                    'country': country,
                    'website': website,
                    'current_systems': current_systems,
                    'social_media': social_media,
                    'notes': notes,
                    'do_not_contact': int(do_not_contact),
                    'removed': 0
                }
                if st.session_state.crm.add_prospect(prospect_data):
                    st.success("Prospect added successfully!")
                else:
                    st.error("Prospect with this EIN already exists!")

    elif page == "View Prospects":
        st.title("View Prospects")
        prospects = st.session_state.crm.get_prospects()
        if not prospects.empty:
            if 'edit_prospect' in st.session_state and st.session_state.edit_prospect is not None:
                prospect = st.session_state.edit_prospect
                st.subheader(f"Edit Prospect: {prospect['organization_name']}")
                with st.form("edit_prospect_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        organization_name = st.text_input("Organization Name", value=prospect['organization_name'])
                        ein = st.text_input("EIN", value=prospect['ein'], disabled=True)
                        contact_name = st.text_input("Contact Name", value=prospect['contact_name'])
                        phone = st.text_input("Phone", value=prospect['phone'])
                        email = st.text_input("Email", value=prospect['email'])
                    with col2:
                        city = st.text_input("City", value=prospect['city'])
                        state = st.text_input("State", value=prospect['state'])
                        country = st.text_input("Country", value=prospect['country'])
                        website = st.text_input("Website", value=prospect['website'])
                    current_systems = st.multiselect(
                        "Current Systems",
                        ["CRM", "ERP", "Accounting", "HR", "Project Management", "Other"],
                        default=json.loads(prospect['current_systems']) if prospect['current_systems'] else []
                    )
                    social_media = json.loads(prospect['social_media']) if prospect['social_media'] else {}
                    st.subheader("Social Media")
                    col1, col2 = st.columns(2)
                    with col1:
                        linkedin = st.text_input("LinkedIn", value=social_media.get('linkedin', ''))
                        twitter = st.text_input("Twitter", value=social_media.get('twitter', ''))
                    with col2:
                        facebook = st.text_input("Facebook", value=social_media.get('facebook', ''))
                        instagram = st.text_input("Instagram", value=social_media.get('instagram', ''))
                    notes = st.text_area("Notes", value=prospect['notes'])
                    do_not_contact = st.checkbox("Do Not Contact", value=bool(prospect.get('do_not_contact', 0)))
                    if st.form_submit_button("Save Changes"):
                        updated_data = {
                            'organization_name': organization_name,
                            'ein': ein,
                            'contact_name': contact_name,
                            'phone': phone,
                            'email': email,
                            'city': city,
                            'state': state,
                            'country': country,
                            'website': website,
                            'current_systems': current_systems,
                            'social_media': {
                                'linkedin': linkedin,
                                'twitter': twitter,
                                'facebook': facebook,
                                'instagram': instagram
                            },
                            'notes': notes,
                            'do_not_contact': int(do_not_contact),
                            'removed': 0
                        }
                        st.session_state.crm.update_prospect(prospect['id'], updated_data)
                        st.success("Prospect updated successfully!")
                        st.session_state.edit_prospect = None
                        st.rerun()
                if st.button("Cancel Edit"):
                    st.session_state.edit_prospect = None
                    st.rerun()
            else:
                for _, prospect in prospects.iterrows():
                    with st.expander(f"{prospect['organization_name']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Contact:** {prospect['contact_name']}")
                            st.write(f"**Phone:** {prospect['phone']}")
                            st.write(f"**Email:** {prospect['email']}")
                            st.write(f"**Location:** {prospect['city']}, {prospect['state']}, {prospect['country']}")
                        with col2:
                            st.write(f"**Website:** {prospect['website']}")
                            st.write(f"**Current Systems:** {', '.join(json.loads(prospect['current_systems']))}")
                            social_media = json.loads(prospect['social_media'])
                            st.write("**Social Media:**")
                            for platform, url in social_media.items():
                                if url:
                                    st.write(f"- {platform}: {url}")
                        st.write(f"**Notes:** {prospect['notes']}")
                        if prospect.get('do_not_contact', 0):
                            st.markdown('<span style="color:red;font-weight:bold;">DO NOT CONTACT</span>', unsafe_allow_html=True)
                        if st.button("Edit", key=f"edit_{prospect['id']}"):
                            st.session_state.edit_prospect = prospect
                            st.rerun()
                        # Soft remove: hide from Prospects but retain in DB/CSV
                        if st.button("Remove from Prospects", key=f"remove_{prospect['id']}"):
                            updated_data = dict(prospect)
                            updated_data['removed'] = 1
                            st.session_state.crm.update_prospect(prospect['id'], updated_data)
                            st.success("Prospect removed from prospects (data retained in DB and CSV).")
                            st.rerun()
        else:
            st.info("No prospects found in the database.")

if __name__ == "__main__":
    main() 