import pandas as pd

def drop_duplicates_reference_master(df: pd.DataFrame) -> pd.DataFrame:
    if "reference" in df.columns and "masterTrackingNumber" in df.columns:
        df_copy = df.copy()
        df_copy["__ref__"] = df_copy["reference"].astype(str).str.strip()
        df_copy["__master__"] = df_copy["masterTrackingNumber"].astype(str).str.strip()
        df_dedup = df_copy.drop_duplicates(subset=["__ref__", "__master__"])
        df_dedup.drop(columns=["__ref__", "__master__"], inplace=True)
        return df_dedup.reset_index(drop=True)
    return df
