# Deployment Guide - HV Screener

This guide covers deploying the Historical Volatility Screener to various platforms.

## 📦 Quick Deployment Checklist

Before deploying, ensure you have:
- ✅ `hv_screener_enhanced.py` - Main application file
- ✅ `requirements.txt` - Python dependencies
- ✅ `asset_list.csv` - Asset database (can also be uploaded via UI)

## 🌐 Streamlit Cloud (Recommended)

### Prerequisites
- GitHub account
- GitHub repository with your code

### Step-by-Step Deployment

#### 1. Prepare Your Repository
```bash
# Create a new directory for your project
mkdir hv-screener
cd hv-screener

# Copy the application files
cp hv_screener_enhanced.py .
cp requirements.txt .
cp asset_list.csv .

# Initialize git repository
git init
git add .
git commit -m "Initial commit: HV Screener"
```

#### 2. Push to GitHub
```bash
# Create a new repository on GitHub (via web interface)
# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/hv-screener.git
git branch -M main
git push -u origin main
```

#### 3. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your GitHub repository
4. Set the main file path: `hv_screener_enhanced.py`
5. Click "Deploy"

The app will be live at: `https://YOUR_USERNAME-hv-screener-XXXXX.streamlit.app`

### Configuration Files

**Optional: `.streamlit/config.toml`**
```toml
[theme]
primaryColor = "#00d4ff"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1e1e1e"
textColor = "#ffffff"

[server]
maxUploadSize = 5
enableCORS = false
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY hv_screener_enhanced.py .
COPY asset_list.csv .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the app
ENTRYPOINT ["streamlit", "run", "hv_screener_enhanced.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run
```bash
# Build the image
docker build -t hv-screener .

# Run the container
docker run -p 8501:8501 hv-screener

# Access at http://localhost:8501
```

### Docker Compose
```yaml
version: '3.8'
services:
  hv-screener:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./asset_list.csv:/app/asset_list.csv
    restart: unless-stopped
```

## 🔧 Local Deployment

### Standard Method
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run hv_screener_enhanced.py

# Access at http://localhost:8501
```

### With Custom Port
```bash
streamlit run hv_screener_enhanced.py --server.port 8080
```

### With Custom Configuration
```bash
streamlit run hv_screener_enhanced.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.maxUploadSize 10
```

## ☁️ Cloud Platforms

### AWS EC2

1. **Launch EC2 Instance**
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.small or larger
   - Security Group: Allow inbound on port 8501

2. **Install Dependencies**
```bash
sudo apt update
sudo apt install python3-pip -y
pip3 install -r requirements.txt
```

3. **Run with Systemd**

Create `/etc/systemd/system/hv-screener.service`:
```ini
[Unit]
Description=HV Screener Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/hv-screener
ExecStart=/usr/local/bin/streamlit run hv_screener_enhanced.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable hv-screener
sudo systemctl start hv-screener
```

### Google Cloud Run

1. **Create Dockerfile** (see Docker section above)

2. **Build and Push to Google Container Registry**
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hv-screener
```

3. **Deploy to Cloud Run**
```bash
gcloud run deploy hv-screener \
  --image gcr.io/YOUR_PROJECT_ID/hv-screener \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Heroku

1. **Create `Procfile`**
```
web: streamlit run hv_screener_enhanced.py --server.port $PORT --server.address 0.0.0.0
```

2. **Create `setup.sh`**
```bash
mkdir -p ~/.streamlit/
echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

3. **Deploy**
```bash
heroku login
heroku create hv-screener
git push heroku main
```

## 📱 Mobile-Friendly Deployment

The app is responsive and works on mobile devices. For best mobile experience:

1. Use Streamlit Cloud (automatic HTTPS)
2. Enable mobile viewport in config:

```toml
[browser]
gatherUsageStats = false

[server]
enableCORS = false
enableXsrfProtection = true
```

## 🔐 Security Considerations

### For Production Deployments

1. **API Rate Limiting**
   - Binance has rate limits (1200 requests/min for Spot, 2400/min for Futures)
   - The app caches data to minimize API calls
   - Consider implementing additional rate limiting for multiple users

2. **Authentication** (Optional)
```python
# Add to the top of your script
import streamlit_authenticator as stauth

# Simple password protection
def check_password():
    def password_entered():
        if st.session_state["password"] == "YOUR_PASSWORD":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()
```

3. **HTTPS**
   - Always use HTTPS in production
   - Streamlit Cloud provides this automatically
   - For custom deployments, use a reverse proxy (nginx) with SSL

## 🔄 Continuous Deployment

### GitHub Actions

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Streamlit Cloud

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Trigger Streamlit Cloud Deployment
        run: echo "Streamlit Cloud auto-deploys on push to main"
```

## 📊 Monitoring

### Application Monitoring

1. **Streamlit Cloud** (built-in)
   - View logs in dashboard
   - Monitor app health
   - Check resource usage

2. **Custom Logging**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hv_screener.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("App started")
```

3. **Performance Tracking**
```python
import time

start_time = time.time()
# ... your code ...
execution_time = time.time() - start_time
logger.info(f"Execution time: {execution_time:.2f}s")
```

## 🛠️ Troubleshooting Deployment Issues

### "Module not found" errors
```bash
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt
```

### "File not found" for asset_list.csv
- Use the file uploader in the app (works everywhere)
- Or ensure file is in the same directory as the script
- Check file permissions

### Memory issues
- Reduce cache TTL for lower memory usage
- Limit number of simultaneous users
- Use a larger instance type

### Slow performance
- Enable Streamlit's caching (already implemented)
- Use a CDN for static assets
- Deploy closer to your users geographically

## 📝 Environment Variables

For sensitive configuration, use environment variables:

```python
import os

# Example: Custom API endpoints
BINANCE_SPOT_URL = os.getenv('BINANCE_SPOT_URL', 'https://api.binance.com/api/v3/klines')
BINANCE_FUTURES_URL = os.getenv('BINANCE_FUTURES_URL', 'https://fapi.binance.com/fapi/v1/klines')
```

Set in Streamlit Cloud:
1. Go to app settings
2. Add secrets in TOML format:
```toml
BINANCE_SPOT_URL = "https://api.binance.com/api/v3/klines"
```

## 🎯 Recommended Setup

**For Development:**
- Local deployment with `streamlit run`

**For Personal Use:**
- Streamlit Cloud (free tier)
- Automatic updates on git push

**For Team/Production:**
- Docker deployment on AWS/GCP
- Add authentication
- Set up monitoring
- Use custom domain

## 📞 Support Resources

- Streamlit Documentation: https://docs.streamlit.io
- Streamlit Community: https://discuss.streamlit.io
- Docker Documentation: https://docs.docker.com

---

**Last Updated**: January 2025
