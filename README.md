# BizVision AI

Business performance ko analyze karne wali intelligent vision.

BizVision AI is an end-to-end AI-powered business analytics platform built with Streamlit, Python, Pandas, Plotly, SQLite, and OpenAI/Ollama-compatible AI workflows.

## Live Demo

Add your Streamlit deployment URL here after publishing:

`https://your-app-name.streamlit.app`

## Key Features

- Secure login with role-based access for users and admins
- Smart CSV/Excel parser for messy business sheets
- Automatic data quality score with missing-value and duplicate checks
- Interactive Plotly dashboards and auto-generated charts
- AI chat for natural-language business insights
- OpenAI, Gemini, Groq, and Ollama-compatible AI provider support
- Forecasting with trend direction and error metrics
- Isolation Forest anomaly detection for unusual business records
- AI-generated PDF business reports
- Admin dataset/report approval workflow
- User management, activity audit trail, and usage monitoring

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Streamlit |
| Backend | Python |
| AI | OpenAI API, Gemini, Groq, Ollama-ready |
| Data | Pandas, NumPy |
| Charts | Plotly |
| ML | scikit-learn |
| Reports | fpdf2 |
| Database | SQLite |

## Demo Accounts

Demo accounts are disabled by default so public deployments do not accidentally expose default credentials.

For first production/admin setup, set:

```bash
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=change-this-long-password
```

For a local-only demo, set:

```bash
ALLOW_DEMO_CREDENTIALS=true
DEMO_ADMIN_PASSWORD=choose-a-demo-admin-password
DEMO_USER_PASSWORD=choose-a-demo-user-password
```

Then start the app. Do not enable this in production.

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m compileall app.py pages utils scripts tests
```

## Docker

```bash
docker build -t bizvision-ai .
docker run -p 8501:8501 bizvision-ai
```

## How To Use

1. Sign in as a user.
2. Upload a CSV/Excel dataset or load the sample dataset.
3. Review the Overview tab for quality score, summary statistics, missing values, and correlations.
4. Use Visualizations for manual and automatic Plotly charts.
5. Add an AI key or Ollama endpoint for AI Chat and PDF report generation.
6. Run forecasting and anomaly detection.
7. Sign in as admin to approve datasets/reports and manage users.

## AI Provider Inputs

Use one of these in the sidebar:

- OpenAI: `sk-...`
- Gemini: `AIzaSy...`
- Groq: `gsk_...`
- Ollama: `ollama=http://localhost:11434`

AI chat and reports send dataset summaries and sample rows to the selected provider. Avoid uploading sensitive production data unless your provider and deployment environment are approved for it.

The app masks common sensitive fields such as emails, phone numbers, card-like numbers, and columns with names like `email`, `phone`, `token`, `secret`, or `password` before sending AI context. Users must also enable AI data-sharing consent in the sidebar.

Ollama works only where the deployed environment can access the Ollama server. For Streamlit Cloud, use hosted API providers such as OpenAI, Gemini, or Groq.

## Email OTP For Password Reset

Forgot Password can send OTPs to the registered user email through SMTP. Configure Streamlit secrets:

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your_email@gmail.com"
password = "your_gmail_app_password"
from_email = "your_email@gmail.com"
```

Use a Gmail App Password or a transactional SMTP provider password. Do not commit real email passwords to GitHub.

Self-registration requires email OTP verification when SMTP is configured. For local demos only, you can bypass this with:

```bash
ALLOW_UNVERIFIED_REGISTRATION=true
```

## Deployment

Recommended deployment: Streamlit Community Cloud.

1. Push this project to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Create a new app from the GitHub repo.
4. Set the main file path as `app.py`.
5. Deploy.

The app creates its SQLite database automatically at startup. Uploaded files and generated local data are temporary on most free cloud deployments, so use an external database/storage service for production.

## Safe Submission Zip

Use the packaging script below instead of manually zipping the folder. It excludes runtime databases, uploaded files, generated reports, `.env`, caches, and Git internals.

```bash
python scripts/build_submission_zip.py
```

## Runtime Limits

Useful production environment variables:

- `MAX_UPLOAD_MB=25`
- `MAX_DATASET_ROWS=100000`
- `MAX_DATASET_COLS=200`
- `ENABLE_RUNTIME_CLEANUP=true`
- `RUNTIME_RETENTION_DAYS=30`

## Project Structure

```text
BizVision_AI/
|-- app.py
|-- requirements.txt
|-- pages/
|   |-- admin_panel.py
|   `-- login_page.py
|-- utils/
|   |-- ai_agent.py
|   |-- auth.py
|   |-- data_analyzer.py
|   |-- data_quality.py
|   |-- forecaster.py
|   |-- report_generator.py
|   `-- visualizer.py
|-- data/
|-- uploads/
|-- reports/
`-- exports/
```

## Production Improvements

- Use PostgreSQL or a managed cloud database for persistent production data
- Use cloud object storage for uploaded files and generated reports
- Store API keys in environment variables or a secrets manager
- Add LangChain/CrewAI orchestration for multi-agent workflows
