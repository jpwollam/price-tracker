# Price Tracker - Backend

A discount notification service that alerts customers via email when tracked electronics items hit their specified price thresholds.

## Quick Start

### 1. Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings (SendGrid API key, etc.)
```

### 3. Initialize & Seed Database

```bash
# Start the app once to create the database
python app.py

# In another terminal, seed with mock products
curl -X POST http://localhost:5000/admin/seed
```

### 4. Test the System

```bash
# Open the web form
open http://localhost:5000

# Create a test alert, then trigger a price check
curl -X POST http://localhost:5000/admin/run-check
```

---

## File Structure

```
price-tracker/
├── app.py              # Main Flask application
├── models.py           # Database table definitions
├── database.py         # Database connection setup
├── price_engine.py     # Price simulation logic
├── checker.py          # Price check + notification logic
├── notifier.py         # Email sending via SendGrid
├── scheduler.py        # APScheduler for automated checks
├── seed_data.py        # Mock product catalog
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── templates/
    └── index.html      # Web form template
```

---

## How It Works

### Data Flow

1. **User submits form** → Email + product + threshold saved to `watches` table
2. **Scheduler runs** (daily or on-demand) → Triggers `checker.py`
3. **Prices update** → `price_engine.py` applies random fluctuation or active sale events
4. **Thresholds checked** → Each watch compared against new prices
5. **Notifications sent** → If threshold met and cooldown expired (3 days)

### Price Simulation

The mock system simulates realistic price behavior:

- **Random fluctuation**: Prices drift -5% to +3% each cycle
- **Flash sales**: 10% chance of 10-25% discount
- **Scripted sales**: Predefined sales override random behavior (for testing)

---

## Admin Endpoints

All admin endpoints are for testing/development. In production, you'd want to add authentication.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/products` | GET | List all products with prices |
| `/admin/watches` | GET | List all active alerts |
| `/admin/sales` | GET | List all sale events |
| `/admin/run-check` | POST | Trigger a price check cycle |
| `/admin/update-prices` | POST | Update prices without notifications |
| `/admin/set-price/<id>/<price>` | POST | Manually set a product's price |
| `/admin/seed` | POST | Seed database with mock data |
| `/admin/seed?email=you@example.com` | POST | Seed + create test alert |
| `/admin/test-email?email=you@example.com` | POST | Send test email |

---

## Testing Workflow

### Test Notification Flow (No Email)

Without SendGrid configured, notifications are logged to console:

```bash
# 1. Start the app
python app.py

# 2. Seed products and create a test watch
curl -X POST "http://localhost:5000/admin/seed?email=test@example.com"

# 3. The seeded data includes an active sale on Sony WH-1000XM5
#    The test watch is set for 20% off, and the sale is 25% off
#    Running a check should trigger a notification

curl -X POST http://localhost:5000/admin/run-check

# 4. Check console output - you should see "[MOCK EMAIL]" logs
```

### Test with Real Email

```bash
# 1. Add your SendGrid API key to .env
SENDGRID_API_KEY=SG.your-actual-key
FROM_EMAIL=alerts@yourdomain.com

# 2. Restart the app
python app.py

# 3. Test email delivery
curl -X POST "http://localhost:5000/admin/test-email?email=your@email.com"

# 4. Create a watch and trigger notification
# Visit http://localhost:5000, create an alert, then:
curl -X POST http://localhost:5000/admin/run-check
```

### Test Specific Price Drops

```bash
# Force a product to a specific price
curl -X POST http://localhost:5000/admin/set-price/1/250.00

# Run check to see if any alerts trigger
curl -X POST http://localhost:5000/admin/run-check
```

---

## Scheduler Options

### Manual Only (Default)

Price checks only run when you call `/admin/run-check`:

```bash
ENABLE_SCHEDULER=false
python app.py
```

### Daily at 8 AM UTC

```bash
ENABLE_SCHEDULER=true
python app.py
```

### Every N Minutes (Testing)

```bash
ENABLE_SCHEDULER=true
CHECK_INTERVAL_MINUTES=5
python app.py
```

---

## Deployment

### Railway / Render / Fly.io

1. Push code to GitHub
2. Connect repository to hosting platform
3. Set environment variables in platform dashboard
4. Deploy

For **Railway**:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Environment Variables for Production

```
SECRET_KEY=<generate-a-strong-random-key>
FLASK_DEBUG=false
SENDGRID_API_KEY=<your-key>
FROM_EMAIL=alerts@yourdomain.com
ENABLE_SCHEDULER=true
```

---

## Next Steps

After validating the mock version:

1. **Register for affiliate programs** (Walmart, Target, eBay, Newegg)
2. **Replace `price_engine.py`** with real API calls
3. **Add affiliate links** to email templates
4. **Deploy** and collect user feedback

---

## Troubleshooting

### "No module named X"

Make sure you've activated your virtual environment and installed dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Emails not sending

- Check that `SENDGRID_API_KEY` is set in `.env`
- Verify your SendGrid account is active
- Check console for error messages

### Database issues

Delete and recreate:

```bash
rm price_tracker.db
python app.py
curl -X POST http://localhost:5000/admin/seed
```
