# CA-GPT Deployment Guide

## Prerequisites
- GitHub account
- OpenAI API key with credits
- Railway or Render account (both have free tiers)

## Option 1: Deploy to Railway (Recommended - Free Tier)

### Steps:

1. **Create GitHub Repository**
   ```bash
   cd /Users/lovishbansal/Documents/cagpt
   git init
   git add .
   git commit -m "Initial commit - CA-GPT application"
   # Create a repo on GitHub, then:
   git remote add origin https://github.com/YOUR_USERNAME/ca-gpt.git
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to https://railway.app
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `ca-gpt` repository
   - Railway will auto-detect it's a Python app

3. **Set Environment Variables**
   In Railway dashboard:
   - Go to your project → Variables
   - Add: `OPENAI_API_KEY` = your-api-key
   - Add: `EMBEDDING_MODEL` = text-embedding-3-large
   - Add: `CHAT_MODEL` = gpt-4o-mini

4. **Deploy**
   - Railway will automatically deploy
   - You'll get a URL like: `https://ca-gpt-production.up.railway.app`

---

## Option 2: Deploy to Render (Also Free Tier)

### Steps:

1. **Create GitHub Repository** (same as above)

2. **Deploy on Render**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub and select `ca-gpt` repo
   - Configure:
     - **Name**: ca-gpt
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn ca_agent_tools:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**
   In Render dashboard:
   - Go to Environment
   - Add: `OPENAI_API_KEY` = your-api-key
   - Add: `EMBEDDING_MODEL` = text-embedding-3-large
   - Add: `CHAT_MODEL` = gpt-4o-mini

4. **Deploy**
   - Click "Create Web Service"
   - You'll get a URL like: `https://ca-gpt.onrender.com`

---

## Important Notes

### API Key Security
- ⚠️ **NEVER commit .env file to GitHub**
- The .gitignore is configured to prevent this
- Only set API keys in the deployment platform's environment variables

### Knowledge Base Files
- Your `kb/*.md` files will be deployed
- The FAISS index will be rebuilt on first run if needed
- Laws.json file should be included in the repo

### Cost Considerations
- Railway/Render free tiers have limits:
  - Railway: 500 hours/month, 512MB RAM
  - Render: 750 hours/month, 512MB RAM
- OpenAI API costs: ~$0.50-$1.00 per 1000 queries with your setup

### Domain (Optional)
- Both Railway and Render allow custom domains
- You can add your own domain in the settings

---

## Testing Your Deployment

Once deployed, test by:
1. Visit your live URL
2. Ask a question like "What is GST?"
3. Check if sources are being displayed
4. Monitor Railway/Render logs for any errors

---

## Troubleshooting

### Build fails
- Check requirements.txt has all dependencies
- Ensure Python version is 3.9+

### App starts but errors on queries
- Verify OPENAI_API_KEY is set correctly
- Check OpenAI account has credits

### Slow responses
- Free tiers have limited resources
- Consider upgrading if needed

---

## Local Development

To run locally after cloning:
```bash
# Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env

# Install dependencies
pip install -r requirements.txt

# Build index
python3 build_kb_index.py

# Run server
python3 ca_agent_tools.py
```

Visit http://localhost:8000
