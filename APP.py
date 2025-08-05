import os
import io
import time
import re
import base64
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from google.cloud import vision
from google.oauth2 import service_account, credentials as gcreds
import gspread
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv
from urllib.parse import quote_plus
from PIL import Image
from flask_cors import CORS
from flask_dance.contrib.google import make_google_blueprint, google
from google.oauth2.credentials import Credentials   # <-- Added for user OAuth!
from flask_dance.consumer import oauth_authorized
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from flask import session, has_request_context, g

# --- Load env ---
load_dotenv()

DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")
DISCOGS_CONSUMER_KEY = os.getenv("DISCOGS_CONSUMER_KEY")
DISCOGS_CONSUMER_SECRET = os.getenv("DISCOGS_CONSUMER_SECRET")
DISCOGS_OAUTH_TOKEN = os.getenv("DISCOGS_OAUTH_TOKEN")
DISCOGS_OAUTH_SECRET = os.getenv("DISCOGS_OAUTH_SECRET")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")

if not all([
    DISCOGS_CONSUMER_KEY, DISCOGS_CONSUMER_SECRET, DISCOGS_OAUTH_TOKEN, DISCOGS_OAUTH_SECRET,
    GOOGLE_CREDENTIALS, EBAY_APP_ID, EBAY_CERT_ID
]):
    raise ValueError("Missing one or more required environment variables.")

# --- Clients ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

creds = service_account.Credentials.from_service_account_file(
    '/etc/secrets/google_creds.json'
).with_scopes(SCOPES)

vision_client = vision.ImageAnnotatorClient(credentials=creds)

# REMOVE this gc from per-user sheet operations! Only use for admin/service stuff if needed!
# gc = gspread.authorize(creds)

def ensure_sheet_headers(sheet):
    expected_headers = [
        'Time of Submission',
        'Matrix Number',
        'Title',
        'Year',
        'Discogs Release',
        'Lowest Price',
        'Median Price',
        'Highest Price'
    ]
    current_headers = sheet.row_values(1)
    if current_headers != expected_headers:
        sheet.resize(rows=1)
        sheet.insert_row(expected_headers, index=1)
        print("✅ Sheet headers updated/set to:", expected_headers)
    else:
        print("✅ Sheet headers already correct.")

auth = OAuth1(
    DISCOGS_CONSUMER_KEY,
    DISCOGS_CONSUMER_SECRET,
    DISCOGS_OAUTH_TOKEN,
    DISCOGS_OAUTH_SECRET
)

# -- Flask App --
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app, supports_credentials=True, origins=[
    "http://localhost:5001", 
    "http://127.0.0.1:5001"
])

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # ONLY for local dev! Remove for production

# Register Google Oauth blueprint
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
)
app.register_blueprint(google_bp, url_prefix='/login')
print(os.getenv("GOOGLE_OAUTH_CLIENT_ID"))
print(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"))

@app.before_request
def inject_user_name():
    if google.authorized:
        try:
            resp = google.get("/oauth2/v2/userinfo")
            if resp.ok:
                full_name = resp.json().get("name", "")
                session['user_first_name'] = full_name.split(" ")[0]
        except TokenExpiredError:
            print("⚠️ Token expired, logging out user.")
            session.clear()
            return redirect(url_for("login"))
        except Exception as e:
            print("⚠️ Exception while injecting user name:", str(e))
            session.pop('user_first_name', None)

# ---- NEW: Helper to get user gspread client ----
def get_user_gspread_client():
    if not google.authorized or not google.token:
        raise Exception("User is not authorized with Google.")
    token = google.token
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )
    import gspread
    return gspread.authorize(creds)

def clean_title(title):
    return re.sub(r"[^\w\s]", "", title)

def extract_matrix_number(text):
    patterns = [
        r'[A-Z]{2,4}\s?-?\s?\d{3,6}\s?[-\u2013]?\s?[A-Z0-9]{1,3}',
        r'ST[- ]?[A-Z]-\d{5}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group().replace(' ', '')
    return None

def search_discogs_by_matrix(matrix_number):
    url = "https://api.discogs.com/database/search"
    headers = {
        'User-Agent': 'VinylScannerApp/1.0 (+https://vinylscanner.local)'
    }
    params = {
        "q": matrix_number,
        "type": "release",
        "per_page": 10,
        "token": DISCOGS_TOKEN
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        results = response.json().get("results", [])
        for r in results:
            print("-", r.get("title"), "|", r.get("catno"), "|", r.get("barcode"))
        for r in results:
            barcodes = r.get("barcode", [])
            if any(matrix_number.replace(" ", "") in b.replace(" ", "") for b in barcodes):
                return r
        return results[0] if results else None
    except Exception as e:
        print("👎🏻 Discogs search error:", e)
        return None

def get_ebay_access_token():
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_ebay_listings(title, year):
    try:
        query = " ".join(clean_title(title).split()) + f" Vinyl {year}"
        print("🔎 eBay query:", query)
        url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={quote_plus(query)}&limit=5"
        access_token = get_ebay_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        print("📤 Full URL:", response.url)
        response.raise_for_status()
        data = response.json()
        items = data.get("itemSummaries", [])
        prices = [
            float(item["price"]["value"])
            for item in items if "price" in item
        ]
        for item in items:
            print("🍭 Found:", item.get("title", "No title"))
        if not prices:
            return None, None, None, "N/A"
        low = min(prices)
        high = max(prices)
        mean = round(sum(prices) / len(prices), 2)
        return low, high, mean
    except Exception as e:
        print("🚩 eBay fetch error:", e)
        return None, None, None, "N/A"

# --- MAIN SCAN POST ENDPOINT: Per-user sheet logic ---
@app.route("/scan", methods=["POST"])
def scan_vinyl():
    try:
        print("✅ Endpoint hit")
        
        if not google.authorized:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("google.login"))
        
        user_sheet_id = session.get('sheet_id')
        if not user_sheet_id:
            return redirect(url_for('connect_sheet'))
        gc = get_user_gspread_client()
        sheet = gc.open_by_key(user_sheet_id).sheet1
        ensure_sheet_headers(sheet)

        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        # OCR scan via Google Vision API with compression
        uploaded_file = request.files["image"]
        image_bytes = uploaded_file.read()
        if uploaded_file.mimetype == "image/jpeg":
            print("🟢 Using original JPEG as-is")
            compressed_bytes = image_bytes
        else:
            print("🟡 Converting and compressing uploaded image")
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            img.thumbnail((800, 800))
            compressed_bytes_io = io.BytesIO()
            img.save(compressed_bytes_io, format="JPEG", quality=75)
            compressed_bytes = compressed_bytes_io.getvalue()

        # Perform OCR on compressed image
        image = vision.Image(content=compressed_bytes)
        ocr_text = vision_client.text_detection(image=image).text_annotations[0].description
        print("🔍 OCR Text:", ocr_text)
        matrix_number = extract_matrix_number(ocr_text)
        print("🔢 Extracted matrix:", matrix_number)
        if not matrix_number:
            return jsonify({"error": "No matrix number found"}), 404
        discogs_result = search_discogs_by_matrix(matrix_number)
        print("🎶 Discogs result:", discogs_result)
        if not discogs_result:
            return jsonify({"error": "No match found on Discogs"}), 404

        title = discogs_result.get("title", "")
        year = str(discogs_result.get("year", ""))
        low_price, high_price, mean_price = fetch_ebay_listings(title, year)
        result = {
            "matrix_number": matrix_number,
            "title": title,
            "year": year,
            "resource_url": discogs_result.get("resource_url", ""),
            "low_price": low_price,
            "high_price": high_price,
            "median_price": mean_price,
        }
        # Log to THIS user's sheet:
        sheet.append_row([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            result.get("matrix_number", ""),
            result.get("title", ""),
            result.get("year", ""),
            result.get("resource_url", ""),
            result.get("low_price", ""),
            result.get("median_price", ""),
            result.get("high_price", ""),
            ""  # ebay_prices column placeholder
        ])
        print("📤 JSON Response to frontend:", {
            "status": "Logged successfully",
            "data": result
        })
        return jsonify({"status": "Logged successfully", "data": result}), 200
    except Exception as e:
        print("🔥 Exception:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    if google.authorized:
        return redirect(url_for('home'))
    return redirect(url_for('landing'))

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/login')
def login():
    if not google.authorized:
        return render_template("login.html")
    return redirect(url_for('home'))

@app.route('/connect_sheet', methods=['GET', 'POST'])
def connect_sheet():
    if not google.authorized:
        return redirect(url_for("google.login"))
    if request.method == "POST":
        user_sheet_url = request.form.get("sheet_url")
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", user_sheet_url)
        sheet_id = match.group(1) if match else user_sheet_url.strip()
        session['sheet_id'] = sheet_id
        return redirect(url_for("home"))
    return render_template("connect_sheet.html")

@app.route('/home')
def home():
    if not google.authorized:
        return redirect(url_for("google.login"))
    if 'sheet_id' not in session:
        return redirect(url_for("connect_sheet"))
    resp = google.get("/oauth2/v2/userinfo")
    user_info = resp.json()
    user_sheet_id = session['sheet_id']
    gc = get_user_gspread_client()
    sheet = gc.open_by_key(user_sheet_id).sheet1
    ensure_sheet_headers(sheet)
    records = list(reversed(sheet.get_all_records()))
    recent_scans = records[:5]  # <-- This defines recent_scans!

    # Tally up the total value from the "Median Price" column (skip blanks/NAs)
    total_value = 0.0
    for row in records:
        price = row.get('Median Price', 0)
        try:
            price = float(price)
            total_value += price
        except (ValueError, TypeError):
            continue
    total_value_str = f"£{total_value:,.2f}"
    return render_template(
        'home.html',
        recent_scans=recent_scans,
        total_value=total_value_str,
        user=user_info
    )

@app.route('/scanner')
def scan_page():
    if not google.authorized:
        return redirect(url_for("google.login"))
    if 'sheet_id' not in session:
        return redirect(url_for("connect_sheet"))
    resp = google.get("/oauth2/v2/userinfo")
    user_info = resp.json()
    return render_template('scan.html', user=user_info)

@app.route('/collection')
def collection():
    if not google.authorized:
        return redirect(url_for("google.login"))
    if 'sheet_id' not in session:
        return redirect(url_for("connect_sheet"))
    resp = google.get("/oauth2/v2/userinfo")
    user_info = resp.json()
    user_sheet_id = session['sheet_id']
    gc = get_user_gspread_client()
    sheet = gc.open_by_key(user_sheet_id).sheet1
    ensure_sheet_headers(sheet)
    records = list(reversed(sheet.get_all_records()))
    return render_template('collection.html', records=records, user=user_info)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
