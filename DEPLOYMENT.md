# Deployment Guide

## Mandatory Submission Checklist

- GitHub repository
- Working deployed demo
- Public deployment link
- Documentation
- PPT or demo video

## Option 1: Streamlit Community Cloud

This is the fastest deployment path for this project.

1. Create a GitHub repository.
2. Upload or push the project files.
3. Make sure these files are present:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `pages/`
   - `utils/`
   - `README.md`
4. Go to `https://streamlit.io/cloud`.
5. Select `New app`.
6. Choose the GitHub repository and branch.
7. Set main file path to `app.py`.
8. Click Deploy.

## Important Notes

- The app creates `data/users.db` automatically.
- Free Streamlit hosting has temporary local storage. Uploaded files may not be permanent.
- For AI Chat and Report generation, users must enter an API key in the sidebar.
- Ollama local endpoints usually do not work on Streamlit Cloud unless the endpoint is publicly reachable.

## Email OTP Setup

Forgot Password sends OTP to the user's registered email when SMTP settings are configured.

In Streamlit Cloud:

1. Open your deployed app.
2. Click `Manage app`.
3. Open `Settings`.
4. Open `Secrets`.
5. Add SMTP credentials:

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your_email@gmail.com"
password = "your_gmail_app_password"
from_email = "your_email@gmail.com"
```

For Gmail, use an App Password, not your normal Gmail password.
After saving secrets, reboot the app.

## GitHub Commands

If Git is installed:

```bash
git init
git add .
git commit -m "Initial AI Business Analyst demo"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

If Git is not installed, use GitHub web upload:

1. Open GitHub.
2. Create a new repository.
3. Upload all project files except ignored runtime files.
4. Do not upload `data/users.db`, `__pycache__`, or uploaded private datasets.

## Demo Video Script

1. Introduce the app as an AI Business Analyst Platform.
2. Login as `demouser`.
3. Load sample dataset or upload CSV/Excel.
4. Show quality score and overview.
5. Show visualizations and auto charts.
6. Ask one AI question if an API key is available.
7. Run forecast.
8. Show anomaly detection.
9. Login as `admin`.
10. Show user management, dataset approval, report approval, usage metrics, and audit logs.

## Submission Text Template

Project Name: AI Business Analyst

Description: An AI-powered analytics platform that converts uploaded business datasets into dashboards, insights, forecasts, anomaly reports, admin approvals, and PDF business reports.

Tech Stack: Streamlit, Python, Pandas, Plotly, SQLite, scikit-learn, OpenAI/Ollama-compatible AI layer.

GitHub Repo: `PASTE_LINK_HERE`

Live Demo: `PASTE_LINK_HERE`

Demo Video/PPT: `PASTE_LINK_HERE`
