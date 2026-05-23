# AI Business Analyst

An end-to-end AI-powered business analytics platform built with Streamlit, Python, Pandas, Plotly, SQLite, and OpenAI/Ollama-compatible AI workflows.

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

## Demo Credentials

The app seeds demo accounts automatically on first run:

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| User | `demouser` | `user123` |

For a real deployment, change or remove these demo credentials.

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown by Streamlit.

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

Ollama works only where the deployed environment can access the Ollama server. For Streamlit Cloud, use hosted API providers such as OpenAI, Gemini, or Groq.

## Deployment

Recommended deployment: Streamlit Community Cloud.

1. Push this project to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Create a new app from the GitHub repo.
4. Set the main file path as `app.py`.
5. Deploy.

The app creates its SQLite database automatically at startup. Uploaded files and generated local data are temporary on most free cloud deployments, so use an external database/storage service for production.

## Project Structure

```text
Ai_business_analyst/
├── app.py
├── requirements.txt
├── pages/
│   ├── admin_panel.py
│   └── login_page.py
├── utils/
│   ├── ai_agent.py
│   ├── auth.py
│   ├── data_analyzer.py
│   ├── data_quality.py
│   ├── forecaster.py
│   ├── report_generator.py
│   └── visualizer.py
├── data/
├── uploads/
├── reports/
└── exports/
```

## Production Improvements

- Replace demo credentials with secure admin onboarding
- Send OTP through email/SMS instead of displaying it in-app
- Store API keys in environment variables or a secrets manager
- Use PostgreSQL or managed cloud database for persistent production data
- Use cloud object storage for uploaded files and generated reports
- Add Docker deployment and CI checks
- Add LangChain/CrewAI orchestration for multi-agent workflows
