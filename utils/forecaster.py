import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

class Forecaster:
    def __init__(self, df, date_col, value_col):
        self.df = df.copy()
        self.date_col = date_col
        self.value_col = value_col

    def forecast(self, periods):
        try:
            working_df = self.df.copy()
            working_df.columns = working_df.columns.astype(str).str.strip()
            target_date_col = str(self.date_col).strip()
            target_val_col = str(self.value_col).strip()

            #  1. Original Dynamic Header Check & Clean Loop 
            if target_date_col not in working_df.columns:
                for i in range(min(15, len(working_df))):
                    row_vals = working_df.iloc[i].astype(str).str.strip().tolist()
                    if any('Timestamp' in str(x) or 'ID' in str(x) for x in row_vals):
                        working_df.columns = working_df.iloc[i].astype(str).str.strip()
                        working_df = working_df.iloc[i+1:].reset_index(drop=True)
                        break
                working_df.columns = working_df.columns.astype(str).str.strip()
                if 'Call Timestamp' in working_df.columns:
                    target_date_col = 'Call Timestamp'

            working_df = working_df.loc[:, ~working_df.columns.str.contains('^Unnamed')]

            if target_date_col not in working_df.columns:
                return None, {"error": f"Column '{target_date_col}' nahi mila."}

            #  2. Super Smart Fiscal Year & Datetime Parser 
            def parse_messy_date(x):
                s = str(x).strip()
                # Agar format "FY '09" ya "FY 09" ya "FY 2009" jaisa hai
                if re.search(r"fy\s*'?\s*(\d{2,4})", s, re.IGNORECASE):
                    match = re.search(r"fy\s*'?\s*(\d{2,4})", s, re.IGNORECASE)
                    yr = match.group(1)
                    if len(yr) == 2:
                        yr = "20" + yr
                    return pd.to_datetime(f"{yr}-12-31")
                # Baki generic dates ke liye standard parser
                return pd.to_datetime(s, errors='coerce')

            working_df['Clean_Date'] = working_df[target_date_col].apply(parse_messy_date)
            working_df = working_df.dropna(subset=['Clean_Date'])

            if working_df.empty:
                return None, {"error": "Date column format parse nahi ho saka."}

            def numeric_series(series):
                if pd.api.types.is_numeric_dtype(series):
                    return pd.to_numeric(series, errors='coerce')
                cleaned = series.astype(str).str.strip()
                accounting_negative = cleaned.str.startswith("(") & cleaned.str.endswith(")")
                cleaned = cleaned.str.replace(r"[$,%\s()]", "", regex=True)
                cleaned = cleaned.mask(accounting_negative & ~cleaned.str.startswith("-"), "-" + cleaned)
                return pd.to_numeric(cleaned, errors='coerce')

            #  3. Dynamic Aggregation Metric Check (Sum vs Count)
            if target_val_col in working_df.columns:
                numeric_values = numeric_series(working_df[target_val_col])
                if numeric_values.notna().sum() >= max(2, int(0.5 * len(working_df))):
                    working_df[target_val_col] = numeric_values
                    grouped_series = working_df.groupby('Clean_Date')[target_val_col].sum()
                else:
                    working_df['temp_date'] = working_df['Clean_Date'].dt.date
                    grouped_series = working_df.groupby('temp_date').size()
            else:
                # Fallback to original volume count logic if column is non-numeric
                working_df['temp_date'] = working_df['Clean_Date'].dt.date
                grouped_series = working_df.groupby('temp_date').size()

            daily_counts = pd.DataFrame({
                'Date': pd.to_datetime(grouped_series.index),
                'Call_Volume': grouped_series.values
            }).sort_values('Date').reset_index(drop=True)

            if len(daily_counts) < 2:
                return None, {"error": "Trends calculate karne ke liye data points kam hain."}

            #  4. Original Seasonality & Linear Polyfit Engine 
            daily_counts['Day_of_Week'] = daily_counts['Date'].dt.dayofweek
            weekday_averages = daily_counts.groupby('Day_of_Week')['Call_Volume'].mean().to_dict()
            overall_mean = daily_counts['Call_Volume'].mean()

            X = np.arange(len(daily_counts))
            Y = daily_counts['Call_Volume'].values
            
            # Safe linear alignment check
            slope, intercept = np.polyfit(X, Y, 1) if len(X) > 1 else (0.0, Y[0])

            daily_counts['Forecast_Trend'] = [
                max(1, int((slope * x + intercept) * 0.4 + weekday_averages.get(d, overall_mean) * 0.6))
                for x, d in zip(X, daily_counts['Day_of_Week'])
            ]

            #  5. Absolute Date Overlap Constraint Check 
            # Force target future timelines strictly after the maximum real past date
            last_real_date = daily_counts['Date'].max()
            
            # Determine correct temporal frequency (Years vs Days spacing)
            is_yearly_data = (daily_counts['Date'].dt.month == 12).all() or daily_counts['Date'].diff().dt.days.mean() > 300
            
            future_dates = []
            for i in range(1, periods + 1):
                if is_yearly_data:
                    future_dates.append(last_real_date + pd.DateOffset(years=i))
                else:
                    future_dates.append(last_real_date + pd.Timedelta(days=i))
            
            future_vals = []
            for i, f_date in enumerate(future_dates, start=len(daily_counts)):
                f_dow = f_date.dayofweek
                base_pred = slope * i + intercept
                seasonality = weekday_averages.get(f_dow, overall_mean)
                
                final_val = (base_pred * 0.4) + (seasonality * 0.6)
                noise = np.random.normal(0, max(1, overall_mean * 0.05)) if len(daily_counts) > 3 else 0
                future_vals.append(max(1, int(round(final_val + noise))))

            future_df = pd.DataFrame({
                'Date': pd.to_datetime(future_dates),
                'Forecast_Trend': future_vals
            })

            #  6. Separated Plotly Interface (Patched for Clear UI Dash Lines) 
            fig = go.Figure()
            
            # Historical Actual Line (Purple)
            fig.add_trace(go.Scatter(
                x=daily_counts['Date'], y=daily_counts['Call_Volume'],
                mode='lines+markers', name='Historical Values', 
                line=dict(color='#7c6af7', width=2.5)
            ))
            
            #  UI FIX: Connect historical last point with forecast first point to remove visual gap
            last_hist_row = daily_counts.iloc[[-1]]
            extended_forecast_df = pd.concat([
                pd.DataFrame({'Date': last_hist_row['Date'], 'Forecast_Trend': last_hist_row['Call_Volume']}),
                future_df
            ], ignore_index=True)
            
            # Future Trend Lines (Green Dashed Line instead of tiny dots)
            fig.add_trace(go.Scatter(
                x=extended_forecast_df['Date'], y=extended_forecast_df['Forecast_Trend'],
                mode='lines+markers', name='Future Projections', 
                #  FIX: mode standard lines+markers ke sath 'dash' ko solid lambi dash line kiya
                line=dict(color='#10b981', width=2.5, dash='dash'),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
            )

            errors = daily_counts['Call_Volume'] - daily_counts['Forecast_Trend']
            metrics = {
                "mae": float(np.mean(np.abs(errors))),
                "rmse": float(np.sqrt(np.mean(errors ** 2))),
                "trend": "Increasing" if slope > 0 else "Decreasing" if slope < 0 else "Stable",
            }
            return fig, metrics

        except Exception as e:
            return None, {"error": str(e)}

