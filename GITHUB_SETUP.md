# GitHub Setup Guide

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Fill in the details:
   - **Repository name:** `healthcare-triage-chatbot`
   - **Description:** `AI-powered medical symptom analysis and triage chatbot with ChatGPT-like conversational capabilities`
   - **Visibility:** Public (or Private if you prefer)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Click "Create repository"

## Step 2: Push to GitHub

After creating the repository, run these commands:

```bash
# Add GitHub remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/healthcare-triage-chatbot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Configure Repository Settings

### Add Topics (for discoverability)
Go to your repository → About (gear icon) → Add topics:
- `healthcare`
- `ai`
- `chatbot`
- `aws`
- `serverless`
- `lambda`
- `dynamodb`
- `medical-triage`
- `groq`
- `llama`

### Add Website URL
In the About section, add:
- **Website:** http://healthcare-triage-chatbot-website-997208471264.s3-website-us-east-1.amazonaws.com

### Enable GitHub Pages (Optional)
If you want to host documentation:
1. Go to Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, folder: /docs
4. Save

## Step 4: Add Repository Description

Update the repository description to:
```
🏥 AI-powered medical triage chatbot with emergency detection, multi-turn conversations, and intelligent symptom analysis. Built with AWS Lambda, DynamoDB, and Groq LLaMA 3.1. Live demo available!
```

## Step 5: Create GitHub Actions (Optional CI/CD)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: |
        cd backend
        pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    - name: Deploy to AWS
      run: |
        chmod +x scripts/package-lambda.sh
        ./scripts/package-lambda.sh
        aws lambda update-function-code \
          --function-name healthcare-triage-chatbot-triage-function \
          --zip-file fileb://backend/lambda.zip
```

## Step 6: Add Secrets (for GitHub Actions)

If using GitHub Actions, add these secrets:
1. Go to Settings → Secrets and variables → Actions
2. Add:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `GROQ_API_KEY`

## Step 7: Create Releases

Create your first release:
1. Go to Releases → Create a new release
2. Tag: `v1.0.0`
3. Title: `Healthcare Triage Chatbot v1.0.0 - Initial Release`
4. Description:
```markdown
## 🎉 Initial Release

### Features
- ✅ AI-powered conversational triage
- ✅ Emergency detection
- ✅ Multi-turn dialogue with context
- ✅ Session management (24-hour persistence)
- ✅ Follow-up question generation
- ✅ Medical entity extraction
- ✅ Production-ready deployment

### Live Demo
http://healthcare-triage-chatbot-website-997208471264.s3-website-us-east-1.amazonaws.com

### Deployment
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for instructions.

### Cost
~$8-12/month for 10,000 conversations

### Tech Stack
- AWS Lambda (Python 3.11)
- DynamoDB
- API Gateway
- Groq LLaMA 3.1
- CloudFormation
```

## Step 8: Add README Badges

Add these badges to the top of your README.md:

```markdown
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](http://healthcare-triage-chatbot-website-997208471264.s3-website-us-east-1.amazonaws.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/)
[![Groq](https://img.shields.io/badge/AI-Groq%20LLaMA-purple.svg)](https://groq.com/)
```

## Step 9: Share Your Project

Share on:
- LinkedIn
- Twitter/X
- Reddit (r/aws, r/serverless, r/Python)
- Dev.to
- Hacker News

Example post:
```
🏥 Just launched an AI-powered medical triage chatbot!

Features:
✅ ChatGPT-like conversations
✅ Emergency detection
✅ Only $8-12/month for 10K conversations
✅ Built with AWS Lambda + Groq LLaMA 3.1

Live demo: [your-url]
GitHub: [your-repo]

#AWS #Serverless #AI #Healthcare
```

## Step 10: Monitor Repository

Enable notifications for:
- Issues
- Pull requests
- Stars
- Forks

---

## Quick Commands Reference

```bash
# Clone your repo
git clone https://github.com/YOUR_USERNAME/healthcare-triage-chatbot.git

# Make changes
git add .
git commit -m "Your commit message"
git push

# Create a new branch
git checkout -b feature/new-feature

# Merge branch
git checkout main
git merge feature/new-feature
git push
```

---

## Repository Stats to Track

- ⭐ Stars
- 🍴 Forks
- 👁️ Watchers
- 📊 Traffic (views, clones)
- 🐛 Issues
- 🔀 Pull requests

---

Good luck with your GitHub repository! 🚀
