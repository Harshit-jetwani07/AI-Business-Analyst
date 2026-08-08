import pandas as pd
import numpy as np


class DataAnalyzer:
    """Automatically analyze a DataFrame and expose typed column lists & stats."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._infer_types()

    #  Type inference 
    def _infer_types(self):
        """Try to parse object columns that look like dates."""
        for col in self.df.select_dtypes(include="object").columns:
            try:
                self.df[col] = pd.to_datetime(self.df[col], infer_datetime_format=True)
            except Exception:
                pass

    #  Column category helpers 
    def get_numeric_columns(self):
        """
        Dynamically extracts columns containing numerical data, 
        even if pandas registered them as objects due to messy rows.
        """
        numeric_cols = []
        for col in self.df.columns:
            # Check if column is native numerical type
            if pd.api.types.is_numeric_dtype(self.df[col]):
                numeric_cols.append(col)
                continue
                
            # If it's an object/string type column, verify the core data composition
            try:
                sample_data = self.df[col].dropna().head(10).astype(str)
                accounting_negative = sample_data.str.strip().str.startswith("(") & sample_data.str.strip().str.endswith(")")
                cleaned_sample = sample_data.str.replace(r'[$,%\s()]', '', regex=True)
                cleaned_sample = cleaned_sample.mask(accounting_negative & ~cleaned_sample.str.startswith("-"), "-" + cleaned_sample)
                converted = pd.to_numeric(cleaned_sample, errors='coerce')
                
                # If majority of non-null samples transform successfully, classify as numeric target
                if converted.notna().sum() >= (0.5 * len(cleaned_sample)) and len(cleaned_sample) > 0:
                    numeric_cols.append(col)
            except:
                pass
                
        return numeric_cols

    def _numeric_frame(self) -> pd.DataFrame:
        numeric_data = {}
        for col in self.get_numeric_columns():
            if pd.api.types.is_numeric_dtype(self.df[col]):
                numeric_data[col] = self.df[col]
            else:
                raw = self.df[col].astype(str).str.strip()
                accounting_negative = raw.str.startswith("(") & raw.str.endswith(")")
                cleaned = raw.str.replace(r'[$,%\s()]', '', regex=True)
                cleaned = cleaned.mask(accounting_negative & ~cleaned.str.startswith("-"), "-" + cleaned)
                numeric_data[col] = pd.to_numeric(cleaned, errors='coerce')
        return pd.DataFrame(numeric_data)

    def get_categorical_columns(self) -> list:
        return self.df.select_dtypes(include=["object", "category"]).columns.tolist()

    def get_date_columns(self) -> list:
        return self.df.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()

    #  Summary statistics 
    def get_summary_stats(self) -> pd.DataFrame:
        num_cols = self.get_numeric_columns()
        if not num_cols:
            return pd.DataFrame()
        return self._numeric_frame().describe()

    #  Column metadata 
    def get_column_info(self) -> dict:
        info = {}
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if "datetime" in dtype:
                col_type = "Date"
            elif self.df[col].dtype in [np.float64, np.int64, np.float32, np.int32]:
                col_type = "Numeric"
            else:
                col_type = "Category"
            info[col] = {
                "Type":     col_type,
                "Non-Null": int(self.df[col].notna().sum()),
                "Unique":   int(self.df[col].nunique()),
            }
        return info

    #  Correlation 
    def get_correlation(self) -> pd.DataFrame:
        num_cols = self.get_numeric_columns()
        if len(num_cols) < 2:
            return pd.DataFrame()
        return self._numeric_frame().corr()

    #  Dataset summary text (for AI context) 
    def get_text_summary(self) -> str:
        lines = [
            f"Dataset shape: {self.df.shape[0]} rows x {self.df.shape[1]} columns",
            f"Columns: {', '.join(self.df.columns.tolist())}",
            f"Numeric columns: {', '.join(self.get_numeric_columns()) or 'None'}",
            f"Categorical columns: {', '.join(self.get_categorical_columns()) or 'None'}",
            f"Date columns: {', '.join(self.get_date_columns()) or 'None'}",
            f"Missing values per column: {self.df.isnull().sum().to_dict()}",
        ]

        num_cols = self.get_numeric_columns()
        if num_cols:
            stats = self._numeric_frame().describe().to_string()
            lines.append(f"\nStatistical summary:\n{stats}")

        # Sample rows
        lines.append(f"\nFirst 5 rows:\n{self.df.head(5).to_string()}")

        return "\n".join(lines)

