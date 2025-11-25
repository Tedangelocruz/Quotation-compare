import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from pypdf import PdfReader
import google.generativeai as genai
from io import BytesIO
import re

# Page Config
st.set_page_config(
    page_title="Quotation Compare",
    page_icon="📊",
    layout="wide"
)

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect('quotations.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS quotations 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, quotation_id INTEGER, 
                  supplier_name TEXT, product_name TEXT, sku TEXT, quantity REAL, 
                  unit_price REAL, total_price REAL)''')
    conn.commit()
    conn.close()

def save_to_db(filename, items):
    conn = sqlite3.connect('quotations.db')
    c = conn.cursor()
    c.execute("INSERT INTO quotations (filename) VALUES (?)", (filename,))
    quotation_id = c.lastrowid
    
    for item in items:
        qty = item.get('quantity') or 0
        price = item.get('unit_price') or 0
        total = item.get('total_price') or (qty * price)
        product_id = item.get('product_id', None)
        
        c.execute("INSERT INTO items (quotation_id, supplier_name, product_name, sku, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (quotation_id, item.get('supplier_name', 'Unknown'), item.get('product_name', 'Unknown'), 
                   product_id, qty, price, total))
    conn.commit()
    conn.close()
    return quotation_id

def get_latest_quotation_items():
    conn = sqlite3.connect('quotations.db')
    # Use pandas for easier dataframe handling
    try:
        # Get latest quotation ID
        latest_q = pd.read_sql_query("SELECT id FROM quotations ORDER BY upload_date DESC LIMIT 1", conn)
        if not latest_q.empty:
            q_id = latest_q.iloc[0]['id']
            items = pd.read_sql_query("SELECT * FROM items WHERE quotation_id = ?", conn, params=(int(q_id),))
            return items
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- Parsing Logic (Ported from app.py) ---
def parse_number(num_str):
    if not isinstance(num_str, str): return num_str
    clean_str = num_str.upper().replace('$', '').replace('€', '').replace('S/', '').replace('USD', '').replace('EUR', '').strip()
    clean_str = clean_str.replace(' ', '')
    if not clean_str: return None

    try:
        if ',' in clean_str and '.' in clean_str:
            last_comma = clean_str.rfind(',')
            last_dot = clean_str.rfind('.')
            if last_comma > last_dot: # 1.234,56
                clean_str = clean_str.replace('.', '').replace(',', '.')
            else: # 1,234.56
                clean_str = clean_str.replace(',', '')
        elif ',' in clean_str: 
            parts = clean_str.split(',')
            if len(parts[-1]) == 2: clean_str = clean_str.replace(',', '.')
            elif len(parts[-1]) == 3: clean_str = clean_str.replace(',', '')
            else: clean_str = clean_str.replace(',', '.')
        return float(clean_str)
    except ValueError:
        return None

def extract_with_llm(text, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = """
        You are a parser that converts PDF price quotations into structured line items.
        You MUST always return a JSON object with a top-level items array.
        Each element in items is an object with:
        supplier_name (string), product_name (string), product_id (string or null),
        quantity (number or null), unit_price (number or null), tax_amount (number or null),
        transport_cost (number or null), total_price (number or null)

        Rules:
        If the PDF is messy or unclear, make your best reasonable guess.
        If some value is missing or not numeric, use null instead of skipping the whole item.
        Never return an empty items array. If you can only find one rough line item, return that.
        Do not include explanations or comments – output ONLY valid JSON.
        
        Here is the text content of the PDF:
        """ + text

        response = model.generate_content(prompt)
        content = response.text
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content)
        if isinstance(data, list):
            return data
        else:
            return data.get('items', [])
    except Exception as e:
        st.error(f"LLM Extraction failed: {str(e)}")
        return []

def extract_items_from_text(text):
    # Simplified heuristic fallback (same logic as app.py but condensed)
    if not text or len(text.strip()) < 10: return []
    items = []
    lines = text.split('\n')
    supplier_name = "Unknown Supplier"
    # Basic supplier detection
    for line in lines[:15]:
        if len(line.strip()) > 3 and "FACTURA" not in line.upper():
            supplier_name = line.strip()
            break
            
    header_keywords = ["DOCUMENTO", "RNC:", "CLIENTE:", "VENDEDOR:", "FECHA:", "TEL:", "PÁGINA", "CANT.", "PRECIO", "DESCRIPCIÓN"]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10: continue
        if any(kw in line.upper() for kw in header_keywords): continue
        
        parts = line.split()
        if len(parts) < 3: continue
        
        # Right-to-left number scanning
        trailing_numbers = []
        text_parts = []
        found_text = False
        
        for i in range(len(parts) - 1, -1, -1):
            val = parse_number(parts[i])
            if val is not None and 0 < val < 1000000 and not found_text:
                trailing_numbers.insert(0, val)
            else:
                found_text = True
                text_parts.insert(0, parts[i])
        
        if len(trailing_numbers) >= 2:
            # Extract logic
            product_id = None
            desc_parts = []
            for part in text_parts:
                if product_id is None and any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
                    product_id = part
                else:
                    desc_parts.append(part)
            
            description = " ".join(desc_parts[:20]) if desc_parts else " ".join(text_parts[:20])
            
            qty = 1.0
            unit_price = 0.0
            total_price = 0.0
            
            if len(trailing_numbers) >= 3:
                qty = trailing_numbers[0]
                unit_price = trailing_numbers[1]
                total_price = trailing_numbers[-1] # Assume last is total
            elif len(trailing_numbers) == 2:
                unit_price = trailing_numbers[0]
                total_price = trailing_numbers[1]
            
            items.append({
                "supplier_name": supplier_name,
                "product_name": description,
                "product_id": product_id,
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": total_price
            })
            
    return items

# --- Main UI ---
init_db()

st.title("📊 Quotation Compare")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key (Optional)", type="password", help="For smart parsing using Google Gemini")
    st.info("Upload a PDF to extract and compare quotation items.")

uploaded_file = st.file_uploader("Upload Quotation (PDF)", type="pdf")

if uploaded_file is not None:
    if st.button("Extract Data", type="primary"):
        with st.spinner("Extracting data..."):
            try:
                reader = PdfReader(uploaded_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                items = []
                if api_key:
                    st.toast("Using Gemini AI for extraction...")
                    items = extract_with_llm(text, api_key)
                    if not items:
                        st.warning("Gemini returned no items, falling back to heuristic parser.")
                        items = extract_items_from_text(text)
                else:
                    st.toast("Using heuristic parser...")
                    items = extract_items_from_text(text)
                
                if items:
                    save_to_db(uploaded_file.name, items)
                    st.success(f"Successfully extracted {len(items)} items!")
                    st.rerun() # Refresh to show data
                else:
                    st.error("Could not extract any items from the PDF.")
            except Exception as e:
                st.error(f"Error processing file: {e}")

# --- Results Area ---
st.divider()
st.subheader("Extracted Items (Latest Upload)")

df = get_latest_quotation_items()

if not df.empty:
    # Display Data
    st.dataframe(
        df, 
        column_config={
            "product_name": "Product",
            "sku": "Product ID",
            "quantity": st.column_config.NumberColumn("Qty", format="%.2f"),
            "unit_price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "total_price": st.column_config.NumberColumn("Total", format="$%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Export Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            "quotations_export.csv",
            "text/csv",
            key='download-csv'
        )
        
    with col2:
        # Excel Export
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Quotations')
        
        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "quotations_export.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='download-excel'
        )

else:
    st.info("No data to display. Upload a PDF to get started.")
