import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


DARK_TEMPLATE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, sans-serif", color="#c0c0e0"),
)

COLOR_SEQ = px.colors.qualitative.Bold


class Visualizer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        for col in self.df.select_dtypes(include="object").columns:
            parsed = pd.to_datetime(self.df[col], errors="coerce", format="mixed")
            if parsed.notna().sum() > 0.7 * self.df[col].notna().sum():
                self.df[col] = parsed

    def _numeric_series(self, col):
        if col not in self.df.columns:
            return pd.Series(dtype=float)
        if pd.api.types.is_numeric_dtype(self.df[col]):
            return pd.to_numeric(self.df[col], errors="coerce")
        cleaned = self.df[col].astype(str).str.replace(r"[$,%\s()]", "", regex=True)
        return pd.to_numeric(cleaned, errors="coerce")

    def _numeric_frame(self, cols):
        return pd.DataFrame({col: self._numeric_series(col) for col in cols if col in self.df.columns})

    def _usable_numeric_cols(self, num_cols):
        usable = []
        for col in num_cols:
            series = self._numeric_series(col)
            if series.notna().sum() >= 2 and series.fillna(0).abs().sum() > 0:
                usable.append(col)
        return usable

    def _usable_category_cols(self, cat_cols):
        usable = []
        for col in cat_cols:
            if col not in self.df.columns:
                continue
            unique_count = self.df[col].dropna().nunique()
            if 2 <= unique_count <= max(50, len(self.df) * 0.8):
                usable.append(col)
        return usable

    def _best_category_col(self, cat_cols):
        usable = self._usable_category_cols(cat_cols)
        if not usable:
            return None
        preferred = [c for c in usable if not str(c).lower().startswith("col_")]
        candidates = preferred or usable
        return max(candidates, key=lambda c: self.df[c].dropna().nunique())

    def _fiscal_year_cols(self, num_cols):
        fy_cols = []
        for col in num_cols:
            match = re.search(r"(?:fy\s*'?\s*)?(\d{2,4})", str(col), re.IGNORECASE)
            if not match:
                continue
            year = match.group(1)
            year_num = int("20" + year if len(year) == 2 else year)
            if 1900 <= year_num <= 2100:
                fy_cols.append((year_num, col))
        return [col for _, col in sorted(fy_cols)]

    def _clean_fig(self, fig, height=440):
        fig.update_layout(
            **DARK_TEMPLATE,
            height=height,
            margin=dict(l=30, r=30, t=55, b=45),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
        return fig

    def _add_numpy_trendline(self, fig, plot_df, x_col, y_col):
        if x_col not in plot_df.columns or y_col not in plot_df.columns:
            return fig
        trend_df = plot_df[[x_col, y_col]].dropna()
        if len(trend_df) < 3 or trend_df[y_col].nunique() < 2:
            return fig
        try:
            if pd.api.types.is_datetime64_any_dtype(trend_df[x_col]):
                x_numeric = trend_df[x_col].astype("int64") / 1e9
                x_line = pd.date_range(trend_df[x_col].min(), trend_df[x_col].max(), periods=50)
                x_line_numeric = x_line.astype("int64") / 1e9
            else:
                x_numeric = pd.to_numeric(trend_df[x_col], errors="coerce")
                valid = x_numeric.notna()
                trend_df = trend_df.loc[valid]
                x_numeric = x_numeric.loc[valid]
                if len(trend_df) < 3 or x_numeric.nunique() < 2:
                    return fig
                x_line_numeric = np.linspace(float(x_numeric.min()), float(x_numeric.max()), 50)
                x_line = x_line_numeric

            slope, intercept = np.polyfit(x_numeric.astype(float), trend_df[y_col].astype(float), 1)
            y_line = slope * x_line_numeric + intercept
            fig.add_trace(go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="Trend",
                line=dict(color="#50fa7b", width=2, dash="dash"),
            ))
        except Exception:
            return fig
        return fig

    def plot(self, chart_type: str, x: str, y: str, color: str = None):
        try:
            plot_df = self.df.copy()
            if y in plot_df.columns:
                plot_df[y] = self._numeric_series(y)
            plot_df = plot_df.dropna(subset=[x])

            if chart_type == "Bar":
                if y in plot_df.columns and plot_df[y].notna().sum() >= 2:
                    agg = plot_df.groupby(x, dropna=True)[y].sum().reset_index()
                    agg = agg[agg[y].notna() & (agg[y] != 0)]
                    if agg.empty:
                        return None
                    agg = agg.reindex(agg[y].abs().sort_values(ascending=False).index).head(15)
                    fig = px.bar(
                        agg.sort_values(y),
                        x=y,
                        y=x,
                        orientation="h",
                        title=f"Top {x} by {y}",
                        color=y,
                        color_continuous_scale="Viridis",
                        template="plotly_dark",
                    )
                else:
                    counts = plot_df[x].value_counts().head(15).reset_index()
                    counts.columns = [x, "Count"]
                    fig = px.bar(counts, x=x, y="Count", title=f"Top {x} by Count", template="plotly_dark")

            elif chart_type == "Line":
                if y not in plot_df.columns or plot_df[y].notna().sum() < 2:
                    return None
                fig = px.line(
                    plot_df.sort_values(x),
                    x=x,
                    y=y,
                    color=color,
                    title=f"{y} Trend by {x}",
                    color_discrete_sequence=COLOR_SEQ,
                    template="plotly_dark",
                )

            elif chart_type == "Scatter":
                if y not in plot_df.columns or plot_df[y].notna().sum() < 2:
                    return None
                fig = px.scatter(
                    plot_df,
                    x=x,
                    y=y,
                    color=color,
                    title=f"{y} vs {x}",
                    color_discrete_sequence=COLOR_SEQ,
                    template="plotly_dark",
                )
                if color is None:
                    fig = self._add_numpy_trendline(fig, plot_df, x, y)

            elif chart_type == "Histogram":
                hist_col = y if y in plot_df.columns else x
                plot_df[hist_col] = self._numeric_series(hist_col)
                if plot_df[hist_col].notna().sum() < 2:
                    return None
                fig = px.histogram(
                    plot_df,
                    x=hist_col,
                    nbins=20,
                    title=f"Distribution of {hist_col}",
                    color_discrete_sequence=["#7c6af7"],
                    template="plotly_dark",
                )

            elif chart_type == "Box":
                if y not in plot_df.columns or plot_df[y].notna().sum() < 2:
                    return None
                fig = px.box(
                    plot_df,
                    x=x,
                    y=y,
                    color=color,
                    title=f"{y} Distribution by {x}",
                    color_discrete_sequence=COLOR_SEQ,
                    template="plotly_dark",
                )

            elif chart_type == "Pie":
                if y in plot_df.columns and plot_df[y].notna().sum() >= 2:
                    counts = plot_df.groupby(x, dropna=True)[y].sum().reset_index()
                    counts = counts[counts[y] > 0].sort_values(y, ascending=False).head(10)
                    value_col = y
                else:
                    counts = plot_df[x].value_counts().head(10).reset_index()
                    counts.columns = [x, "count"]
                    value_col = "count"
                if counts.empty:
                    return None
                fig = px.pie(
                    counts,
                    names=x,
                    values=value_col,
                    title=f"{value_col} Share by {x}",
                    color_discrete_sequence=COLOR_SEQ,
                    template="plotly_dark",
                )
            else:
                return None

            return self._clean_fig(fig, height=470)
        except Exception:
            return None

    def generate_auto_charts(self, num_cols, cat_cols, date_cols):
        figs = []
        num_cols = self._usable_numeric_cols(num_cols)
        metric_col = self._best_category_col(cat_cols)
        fy_cols = self._fiscal_year_cols(num_cols)
        latest_col = fy_cols[-1] if fy_cols else (num_cols[0] if num_cols else None)

        if metric_col and latest_col:
            plot_df = self.df[[metric_col]].copy()
            plot_df[latest_col] = self._numeric_series(latest_col)
            plot_df = plot_df.dropna(subset=[metric_col, latest_col])
            plot_df = plot_df[plot_df[latest_col] != 0]
            if not plot_df.empty:
                agg = plot_df.groupby(metric_col, dropna=True)[latest_col].sum().reset_index()
                agg = agg.reindex(agg[latest_col].abs().sort_values(ascending=False).index).head(12)
                fig = px.bar(
                    agg.sort_values(latest_col),
                    x=latest_col,
                    y=metric_col,
                    orientation="h",
                    title=f"Top {metric_col} by {latest_col}",
                    color=latest_col,
                    color_continuous_scale="Viridis",
                    template="plotly_dark",
                )
                figs.append(self._clean_fig(fig, height=520))

        if latest_col:
            dist = self._numeric_series(latest_col).dropna()
            if len(dist) >= 3 and dist.abs().sum() > 0:
                fig = px.histogram(
                    pd.DataFrame({latest_col: dist}),
                    x=latest_col,
                    nbins=20,
                    title=f"Distribution of {latest_col}",
                    color_discrete_sequence=["#7c6af7"],
                    template="plotly_dark",
                )
                figs.append(self._clean_fig(fig, height=430))

        if len(fy_cols) >= 2:
            trend_df = self._numeric_frame(fy_cols)
            totals = trend_df.sum(axis=0).reset_index()
            totals.columns = ["Fiscal Year", "Total Value"]
            fig = px.line(
                totals,
                x="Fiscal Year",
                y="Total Value",
                markers=True,
                title="Total Value Trend Across Fiscal Years",
                color_discrete_sequence=["#50fa7b"],
                template="plotly_dark",
            )
            figs.append(self._clean_fig(fig, height=430))
        elif date_cols and latest_col:
            dc = date_cols[0]
            nc = latest_col
            ts_df = self.df.copy()
            ts_df[nc] = self._numeric_series(nc)
            ts = ts_df.groupby(pd.Grouper(key=dc, freq="ME"))[nc].sum().reset_index()
            ts = ts[ts[nc].notna() & (ts[nc] != 0)]
            if len(ts) >= 2:
                fig = px.line(
                    ts,
                    x=dc,
                    y=nc,
                    title=f"{nc} Over Time",
                    color_discrete_sequence=["#50fa7b"],
                    template="plotly_dark",
                )
                figs.append(self._clean_fig(fig, height=430))

        if metric_col and len(fy_cols) >= 2:
            heat = self.df[[metric_col] + fy_cols].copy()
            for col in fy_cols:
                heat[col] = self._numeric_series(col)
            heat["_score"] = heat[fy_cols].abs().sum(axis=1)
            heat = heat.dropna(subset=[metric_col]).sort_values("_score", ascending=False).head(12)
            if not heat.empty and heat["_score"].sum() > 0:
                fig = px.imshow(
                    heat[fy_cols].values,
                    x=fy_cols,
                    y=heat[metric_col].astype(str),
                    color_continuous_scale="Viridis",
                    title=f"Top {metric_col} Across Fiscal Years",
                    template="plotly_dark",
                    aspect="auto",
                )
                figs.append(self._clean_fig(fig, height=520))

        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
            scatter_df = self.df.copy()
            scatter_df[x_col] = self._numeric_series(x_col)
            scatter_df[y_col] = self._numeric_series(y_col)
            scatter_df = scatter_df.dropna(subset=[x_col, y_col])
            if len(scatter_df) >= 4 and scatter_df[x_col].nunique() > 1 and scatter_df[y_col].nunique() > 1:
                color_col = metric_col if metric_col and scatter_df[metric_col].nunique() <= 12 else None
                fig = px.scatter(
                    scatter_df,
                    x=x_col,
                    y=y_col,
                    color=color_col,
                    title=f"{x_col} vs {y_col}",
                    color_discrete_sequence=COLOR_SEQ,
                    template="plotly_dark",
                )
                if color_col is None:
                    fig = self._add_numpy_trendline(fig, scatter_df, x_col, y_col)
                figs.append(self._clean_fig(fig, height=430))

        return figs
