"""
XLSX parser service
Extracts text from XLSX files
"""

import pandas as pd

def extract_text(path):
    """Extract text from XLSX file"""
    dfs = pd.read_excel(path, sheet_name=None)
    return "\n\n".join(df.to_string() for df in dfs.values())

