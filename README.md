# PlayoffPurge - Fantasy Football Playoff Dashboard

A lightweight web dashboard for managing a guillotine-style fantasy football playoff league, powered by Google Sheets as the database.

## 🏈 Features

- **Single-page dashboard** showing all teams ranked by seed
- **Expandable team cards** to view detailed rosters
- **Real-time data** from Google Sheets (cached for performance)
- **Mobile-friendly** responsive design
- **Guillotine-style tracking** with eliminated/active/champion status
- **Zero database setup** - just use Google Sheets!

## 🎯 League Rules

- **Guillotine format**: Bottom teams eliminated each week
- **FanDuel scoring**: 4pt passing TD + 0.5 PPR
- **Weekly draft**: 5 players per team
- **Changing roster requirements** each playoff round
- **Progressive payout structure**: $20/week + $100 Superbowl

## 📋 Google Sheet Schema

### Tab 1: League_Meta
Key-value pairs for league information:

| key          | value                |
|--------------|----------------------|
| league_name  | PlayoffPurge 2025    |
| current_week | Week 18              |
| last_updated | 2025-01-05 14:30:00  |

### Tab 2: Teams
All team information:

| team_id | owner_name | team_name        | seed | status      | total_points | current_week |
|---------|------------|------------------|------|-------------|--------------|--------------|
| 1       | Goober     | Goober's Goons   | 1    | active      | 127.5        | Week 18      |
| 2       | Kevin      | Kevin's Killers  | 2    | active      | 115.2        | Week 18      |
| 3       | Kathleen   | Kat's Krew       | 3    | eliminated  | 98.4         | Week 18      |

**Status values**: `active`, `eliminated`, `champion`

### Tab 3: Rosters
Player details for each team:

| team_id | week    | position | player_name         | team | points | status |
|---------|---------|----------|---------------------|------|--------|--------|
| 1       | Week 18 | QB       | Patrick Mahomes     | KC   | 24.5   | active |
| 1       | Week 18 | RB       | Christian McCaffrey | SF   | 18.2   | active |
| 1       | Week 18 | RB       | Bijan Robinson      | ATL  | 15.8   | active |

### Tab 4: Roster_Requirements (Reference)
Weekly roster rules:

| week         | teams_left | positions_required                  | payout |
|--------------|------------|-------------------------------------|--------|
| Week 18      | 9          | QB,RB,RB,WR,WR                     | $20    |
| Wildcard     | 8          | QB,RB,WR,FLEX,FLEX                 | $20    |
| Divisional   | 6          | SUPERFLEX,RB,WR,FLEX,FLEX          | $20    |
| Championship | 4          | SUPERFLEX,FLEX,FLEX,FLEX,FLEX      | $20    |
| Superbowl    | 2          | SUPERFLEX,FLEX,FLEX,FLEX,FLEX      | $100   |

### 📝 How to Update Data

1. **Update player points** in the Rosters tab after games complete
2. **Calculate total_points** in Teams tab using formula: `=SUMIF(Rosters!A:A, A2, Rosters!F:F)`
3. **Update team status** manually when teams are eliminated
4. **Update last_updated** timestamp in League_Meta

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud account (free)
- Google Sheet (copy provided template)

### 1. Google Cloud Setup

```bash
# Visit https://console.cloud.google.com
# Create new project: "PlayoffPurge"
# Enable Google Sheets API: APIs & Services → Library → Google Sheets API
# Create Service Account:
#   - IAM & Admin → Service Accounts → Create Service Account
#   - Name: "playoff-purge-readonly"
#   - Role: None (we'll use sheet sharing instead)
#   - Create Key → JSON → Download
```

Save the JSON file as `credentials/service-account.json`

**Important**: Copy the service account email (e.g., `playoff-purge@project-id.iam.gserviceaccount.com`)

### 2. Google Sheet Setup

1. Create a new Google Sheet
2. Create 4 tabs: `League_Meta`, `Teams`, `Rosters`, `Roster_Requirements`
3. Add column headers as shown in schema above
4. **Share the sheet** with your service account email (Viewer access)
5. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
   ```

### 3. Local Development Setup

```bash
# Clone or navigate to project directory
cd PlayoffPurge

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create credentials directory
mkdir credentials
# Place your service-account.json file in credentials/

# Configure environment variables
cp .env.example .env
# Edit .env with your SHEET_ID

# Run the application
uvicorn main:app --reload --port 8000
```

Visit: http://localhost:8000

### 4. Environment Variables

Edit `.env` file:

```env
GOOGLE_SHEET_ID=your_actual_sheet_id_here
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json
CACHE_TTL_SECONDS=300
ADMIN_PASSWORD=your_secure_password
APP_TITLE=PlayoffPurge 2025
```

## 🌐 Deployment to Render

### Option 1: Render Dashboard (Recommended)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin your-repo-url
   git push -u origin main
   ```

2. **Create Render Web Service**:
   - Go to https://render.com
   - New → Web Service
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Add Environment Variables** in Render dashboard:
   ```
   GOOGLE_SHEET_ID = your_sheet_id
   GOOGLE_APPLICATION_CREDENTIALS_JSON = {paste entire JSON file content}
   ADMIN_PASSWORD = secure_password_here
   ```

4. **Deploy**: Click "Create Web Service"

### Option 2: Manual Render Setup

If not using `render.yaml`:

- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Add all environment variables** listed above

## 🔒 Security Notes

### ✅ Best Practices Implemented

- Service account credentials stored as environment variable
- Google Sheet shared only with service account (no public access)
- Admin endpoints protected with HTTP Basic Auth
- Read-only Sheets API access
- Rate limiting with 5-minute cache TTL
- HTTPS enforced by Render
- No sensitive data in repository

### 🔐 Access Control

- **Public Access**: Dashboard is read-only (anyone with URL can view)
- **Admin Access**: `/refresh` endpoint requires authentication
  - Username: `admin`
  - Password: Set via `ADMIN_PASSWORD` env var

### 🛡️ Sheet Security Checklist

- [ ] Service account credentials NOT committed to git
- [ ] Google Sheet shared ONLY with service account email
- [ ] Sheet access set to "Viewer" (read-only)
- [ ] Strong admin password set in production
- [ ] `.env` file in `.gitignore`

## 📡 API Endpoints

### Public Endpoints

- `GET /` - Main dashboard (HTML)
- `GET /health` - Health check for monitoring
- `GET /api/teams` - Teams data as JSON

### Protected Endpoints

- `POST /refresh` - Clear cache and force data refresh
  - Requires HTTP Basic Auth (admin / your_password)
  - Example with curl:
    ```bash
    curl -X POST https://your-app.onrender.com/refresh \
      -u admin:your_password
    ```

## 🎨 Tech Stack

- **Backend**: FastAPI (async Python web framework)
- **Data Source**: Google Sheets API
- **Templates**: Jinja2 (server-rendered HTML)
- **Styling**: Pure CSS (no frameworks)
- **Caching**: In-memory TTL cache (cachetools)
- **Deployment**: Render (free tier)

### Why FastAPI?

- ✅ Built-in async support for API calls
- ✅ Automatic API documentation
- ✅ Modern Python with type hints
- ✅ Fast and lightweight
- ✅ Easy deployment to serverless platforms

### Why Service Account over OAuth?

- ✅ No user login flow required
- ✅ Simpler deployment (one credential file)
- ✅ Perfect for read-only dashboards
- ✅ No token refresh logic needed

## 🧩 Project Structure

```
PlayoffPurge/
├── main.py                     # FastAPI application
├── sheets_client.py            # Google Sheets data layer
├── models.py                   # Data models (Team, Player, etc.)
├── config.py                   # Settings & environment variables
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment config
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── credentials/               # Service account JSON (gitignored)
│   └── .gitkeep
├── templates/                 # Jinja2 HTML templates
│   ├── index.html            # Main dashboard
│   └── team_card.html        # Team card component
└── static/                    # Static assets
    └── styles.css            # CSS styles
```

## 🔧 Customization

### Change Cache Duration

In `.env`:
```env
CACHE_TTL_SECONDS=60   # Refresh every 1 minute
CACHE_TTL_SECONDS=600  # Refresh every 10 minutes
```

### Update League Name

In Google Sheet `League_Meta` tab or `.env`:
```env
APP_TITLE=My Custom League Name
```

### Styling

Edit `static/styles.css` to customize colors, fonts, and layout.

## 🐛 Troubleshooting

### Error: "Failed to load dashboard"

1. Check Google Sheet ID is correct in `.env`
2. Verify service account has access to the sheet
3. Ensure sheet tabs are named exactly: `League_Meta`, `Teams`, `Rosters`
4. Check credentials JSON file is valid

### Error: "403 Permission Denied"

- Sheet not shared with service account email
- Share the Google Sheet with the email from your service-account.json

### Error: "No module named 'google'"

```bash
pip install -r requirements.txt
```

### Data not updating

- Clear cache: `POST /refresh` endpoint (with admin auth)
- Check `last_updated` timestamp in League_Meta tab
- Default cache: 5 minutes

## 💰 Cost Breakdown

- **Google Sheets API**: FREE (up to 60 requests/min)
- **Render Deployment**: FREE tier (750 hours/month)
- **Total Monthly Cost**: $0 ✅

## 📝 Weekly Workflow

1. **Before games**: Draft players and add to Rosters tab
2. **During games**: Monitor scores (optional real-time updates)
3. **After games**: 
   - Update player points in Rosters tab
   - Teams tab will auto-calculate totals (if using formulas)
   - Update team status for eliminated teams
   - Update last_updated timestamp
4. **View dashboard**: Refresh to see updated standings

## 🚀 Future Enhancements (Optional)

- [ ] Auto-refresh frontend (polling or WebSocket)
- [ ] Historical data / previous weeks
- [ ] Player stats API integration (ESPN/Yahoo)
- [ ] Admin panel for editing data
- [ ] Email notifications for eliminations
- [ ] League chat/comments
- [ ] Mobile app version

## 📄 License

MIT License - Feel free to use and modify for your league!

## 🤝 Contributing

Found a bug or have a feature request? Open an issue or submit a PR!

## 🏆 Credits

Built for the PlayoffPurge league with ❤️ and ☕

---

**Ready to deploy?** Follow the setup steps above and your dashboard will be live in minutes!
