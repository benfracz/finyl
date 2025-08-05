# 🎶 Finyl: AI-Powered Vinyl Record Scanner

**Finyl** is a web app that helps vinyl collectors identify, value, and catalogue their records. Users simply take a photo of the matrix number (etched on the inner groove of a vinyl record), and Finyl uses AI and public APIs to:

- Extract the matrix number via **OCR**
- Identify the release via **Discogs API**
- Estimate its value via **eBay API**
- Log everything to the user’s **Google Sheet**

> 🔐 Each user connects their own Google account via OAuth2 and maintains private control of their personal collection.

---

## 🚀 Live App

🔗 [https://finyl.onrender.com](https://finyl.onrender.com)

---

## 📸 Features

- 🔍 Dead wax OCR using Google Vision API  
- 🎼 Discogs release identification  
- 💸 eBay pricing integration  
- 📊 Google Sheets integration per user (OAuth2)  
- 🔒 Google Sign-In for each user  
- 📱 Responsive UI (Figma → Anima export)

---

## 🧠 How It Works

1. User signs in via Google
2. User connects their Google Sheet
3. User uploads a photo of the vinyl matrix
4. Finyl:
   - Extracts matrix number (Google Vision API)
   - Finds the record (Discogs)
   - Fetches prices (eBay)
   - Logs the data to user's Google Sheet

---

## 🧰 Tech Stack

| Layer         | Technology                            |
|--------------|----------------------------------------|
| Frontend      | HTML, CSS, JS (Anima + Figma export) |
| Backend       | Python (Flask)                        |
| Auth          | `flask-dance` + Google OAuth2         |
| OCR           | Google Cloud Vision API               |
| Data          | Discogs API                           |
| Pricing       | eBay Browse API                       |
| Storage       | Google Sheets via `gspread`           |
| Deployment    | [Render](https://render.com)          |

---

## 🔐 Google OAuth2

- Auth handled with `flask-dance`
- Scopes requested:
  - `https://www.googleapis.com/auth/spreadsheets`
  - `https://www.googleapis.com/auth/drive.file`
  - `openid`, `email`, `profile`
- Each user connects their own sheet
- No service account is used

---

## 📂 Project Structure

