# Quotation Compare 📊

A powerful tool to extract, analyze, and compare quotation items from PDF files using Google Gemini AI.

## Features

- **📄 PDF Extraction**: Automatically parses complex PDF quotations.
- **🤖 AI-Powered**: Uses Google Gemini 2.5 Flash for intelligent data extraction.
- **💾 Database**: Stores all extracted items in a local SQLite database.
- **📉 Export**: Download data as CSV or formatted Excel (.xlsx) files.
- **⚡ Streamlit App**: Modern, interactive web interface.

## How to Run Locally

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App**:
   ```bash
   streamlit run streamlit_app.py
   ```

## Deployment on Streamlit Cloud

1. Upload this code to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub account.
4. Select the repository and the main file: `streamlit_app.py`.
5. **Important**: In the "Advanced Settings" of the deployment, add your `GOOGLE_API_KEY` as a secret if you want to use the AI features.

## Project Structure

- `streamlit_app.py`: Main application file.
- `app.py`: Legacy Flask application.
- `quotations.db`: SQLite database (auto-generated).
- `requirements.txt`: Python dependencies.
