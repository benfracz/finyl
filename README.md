# 🎶 Finyl: AI-Powered Vinyl Record Scanner

**Finyl** is a Flask web app that helps vinyl collectors identify, value, and catalogue their records. Users simply upload a photo of the matrix number (etched into the dead wax of the vinyl), and Finyl handles the rest:

- 📸 Extracts the matrix via OCR (Google Vision API)  
- 🎼 Identifies the record via Discogs  
- 💰 Estimates resale prices via eBay  
- 📊 Logs the data into the user's own Google Sheet  

---

## 🚀 Live App

🔗 https://finyl.onrender.com

---

## 📸 Key Features

- ✅ **Google Sign-In** (via OAuth2)  
- 📎 **User-connected Google Sheets** (no service account needed)  
- 🔍 **OCR matrix detection** via Google Cloud Vision API  
- 💿 **Discogs API** to identify record release  
- 💸 **eBay API** to estimate low/median/high prices  
- 📝 **User sheet logging** (with timestamp + data)  
- 🎨 Clean, responsive UI from Figma + Anima  

---


## 📦 Design Philosophy: Decentralised Storage via Google Sheets

Instead of hosting a central database, Finyl uses **Google OAuth2** to allow each user to connect their **own Google Sheet** as a personal database. This approach:

- 💸 **Eliminates the cost** of managing and scaling server-side databases  
- 🔐 **Gives users full ownership** and visibility over their data  
- 📤 **Stores records transparently** in the user's own Google Drive  
- 🌍 **Localises data storage** to each user's Google Cloud account  

By leveraging Google Sheets as a lightweight backend, Finyl delivers a privacy-conscious, scalable, and low-overhead experience that aligns with how collectors already manage personal inventories.

---

## 🧠 How It Works

1. User signs in via Google  
2. User pastes their Google Sheet link  
3. User uploads a vinyl image  
4. App:  
   - Extracts matrix number with OCR  
   - Queries Discogs for release info  
   - Fetches prices from eBay  
   - Logs everything to their own sheet  

---

## 🧰 Tech Stack

| Layer     | Technology                     |
|-----------|--------------------------------|
| Frontend  | HTML, CSS, JS (Figma + Anima)  |
| Backend   | Python (Flask)                 |
| Auth      | Flask-Dance + Google OAuth2    |
| OCR       | Google Cloud Vision API        |
| Vinyl ID  | Discogs API                    |
| Pricing   | eBay Browse API                |
| Storage   | Google Sheets via `gspread`    |
| Hosting   | Render                         |

---

## 🔐 Google OAuth2

- OAuth handled via `flask-dance.contrib.google`  
- Scopes requested:
  - `openid`
  - `email`
  - `profile`
  - `https://www.googleapis.com/auth/drive.file`
  - `https://www.googleapis.com/auth/spreadsheets`  
- Each user connects their own sheet  
- **No service account** is used  

---

## 📂 Project Structure

```
finyl/
├── APP.py                  # Flask app & route logic
├── scanner_logic.py        # OCR + Discogs + eBay logic
├── templates/              # HTML pages
│   ├── landing.html
│   ├── login.html
│   ├── home.html
│   ├── scan.html
│   └── collection.html
├── static/
│   ├── img/                # PNG assets (logos, examples)
│   └── styles/             # CSS files
├── requirements.txt
├── .env                    # Local secrets (not committed)
└── README.md
```

---

## ⚙️ Local Setup

### 1. Clone the Repo

```bash
git clone https://github.com/benfracz/finyl.git
cd finyl
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

```
FLASK_SECRET_KEY=your_secret
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
DISCOGS_USER_TOKEN=your_discogs_token
EBAY_APP_ID=your_ebay_app_id
```

### 5. Run Flask App

```bash
flask run --port=5001
```

Then visit: `http://localhost:5001`

---

## 🧪 APIs Used

| API               | Purpose                            |
|-------------------|------------------------------------|
| Google Vision     | OCR matrix number extraction       |
| Discogs API       | Vinyl record identification        |
| eBay Browse API   | Price estimates (low/mean/high)    |
| Google Sheets API | Record collection logging          |

---

## 🛡️ Security Notes

- No service account — uses **user-granted OAuth tokens**
- Secrets are hidden in `.env` (never committed)
- OAuth tokens are stored securely via Flask session
- Each user owns and controls their data

---

## 🌍 Deployment (Render)

- Render web service
  - Start command: `gunicorn APP:app`
  - Secrets added via Render Dashboard as environment variables
- Hosted here:  
  🔗 https://finyl.onrender.com

---

## ✨ Future Features

- ✅ Multi-image support for better OCR  
- 📈 Price history charting (via eBay data)  
- 📦 Export collection as PDF  
- 📱 Progressive Web App version  
- 💬 Shareable scan summaries  

---

## 🙌 Built By

**Ben Fracz**  
🔗 [github.com/benfracz](https://github.com/benfracz)  

Designed in Figma + Anima  
Built with Flask, Google Cloud, and CodePen.

---

## 📜 License

MIT License – see `LICENSE` file for details.
