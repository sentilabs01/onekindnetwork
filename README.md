# OneKind Network - Nonprofit Search Engine

A powerful vectorized search engine for nonprofit organizations, built with Python and Streamlit. This tool allows users to search through nonprofit data using semantic search capabilities.

## Features

- 🔍 Semantic search across nonprofit databases
- 📊 Displays 10 most relevant results
- 📝 Shows comprehensive organization details including:
  - EIN numbers
  - Organization names
  - Locations
  - Websites
  - Email addresses
- 🔗 Quick Google search integration for further research
- 🧹 Automatic duplicate removal based on EIN numbers

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sentilabs01/onekindnetwork.git
cd onekindnetwork
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run search_engine.py
```

2. Open your browser and navigate to the provided local URL (typically http://localhost:8501)

3. Enter your search query in the search box

4. View and expand results to see detailed information about each nonprofit organization

## Project Structure

```
onekindnetwork/
├── search_engine.py          # Main search engine implementation
├── search_engine_backup.py   # Backup of the working version
├── requirements.txt          # Python dependencies
├── international nonprofits/ # Directory containing international nonprofit data
└── IA nonprofits/           # Directory containing IA nonprofit data
```

## Dependencies

- pandas>=1.3.0
- numpy>=1.21.0
- sentence-transformers>=2.2.0
- faiss-cpu>=1.7.0
- streamlit>=1.0.0
- chardet>=4.0.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details. 