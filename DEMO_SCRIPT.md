# Demo Script

## 30-Second Introduction

BizVision AI is an end-to-end business intelligence platform for analyzing business performance with intelligent AI vision. A user can upload CSV or Excel data, and the app automatically parses the dataset, checks quality, generates dashboards, creates Plotly charts, answers business questions with AI, forecasts future trends, detects anomalies, and generates PDF reports. The admin panel adds governance through user management, dataset/report approvals, activity logs, and AI usage monitoring.

## Demo Flow

1. Login as `demouser`.
2. Load sample dataset or upload a CSV/Excel file.
3. Open Overview:
   - rows, columns, numeric columns
   - missing values
   - data quality score
   - data preview
   - statistical summary
   - correlation heatmap
4. Open Visualizations:
   - manual chart controls
   - auto-generated business charts
5. Open AI Chat:
   - enter API key if available
   - ask: `Give me a business summary of this dataset`
6. Open Forecast:
   - choose date and metric
   - run forecast
   - show MAE, RMSE, and trend
7. Open Anomalies:
   - show unusual records and anomaly scores
8. Open Report:
   - explain report generation unlocks after admin review for normal users
9. Logout and login as `admin`.
10. Open Admin Panel:
    - show user management
    - show dataset approval queue
    - show report approval queue
    - show AI usage metrics
    - show activity logs and per-user timeline

## Strong Differentiator

Most dashboards only upload data and show charts. This project covers the complete analytics workflow: smart data parsing, quality scoring, AI insights, forecasting, anomaly detection, PDF reporting, admin approvals, user management, audit logging, and AI cost monitoring.

## Production-Ready Talking Point

This is demo-ready and architected for production extension. For production, I would add email/SMS OTP delivery, environment-based secrets, managed PostgreSQL, cloud file storage, and a LangChain/CrewAI multi-agent layer for advanced workflow orchestration.
