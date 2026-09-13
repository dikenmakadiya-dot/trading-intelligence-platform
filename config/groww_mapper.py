"""
Groww Chart URL Mapper Utility
Generates direct hyperlinks to official Groww stock charts on NSE:
https://groww.in/charts/stocks/<slug>?exchange=NSE
"""

import os
import csv
import re
from typing import Dict, Optional

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
N500_FILE = os.path.join(CONFIG_DIR, "ind_nifty500list.csv")
MICRO250_FILE = os.path.join(CONFIG_DIR, "ind_niftymicrocap250_list.csv")

_SYMBOL_TO_COMPANY: Dict[str, str] = {}
_SYMBOL_TO_SLUG: Dict[str, str] = {}

def clean_company_slug(name: str) -> str:
    """
    Converts company name to standardized Groww URL slug:
    e.g. "Graphite India Ltd." -> "graphite-india-ltd"
    """
    if not name:
        return ""
    s = name.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def _load_registry():
    global _SYMBOL_TO_COMPANY, _SYMBOL_TO_SLUG
    if _SYMBOL_TO_COMPANY:
        return
    for filepath in [N500_FILE, MICRO250_FILE]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sym = (row.get("Symbol") or "").strip().upper()
                        company = (row.get("Company Name") or "").strip()
                        if sym and company:
                            _SYMBOL_TO_COMPANY[sym] = company
                            _SYMBOL_TO_SLUG[sym] = clean_company_slug(company)
            except Exception:
                pass

def get_groww_chart_url(symbol: str, company_name: Optional[str] = None) -> str:
    """
    Returns verified Groww chart URL for any NSE stock.
    Fallback pattern: if symbol unknown, uses slug of symbol or provided name.
    """
    _load_registry()
    sym = (symbol or "").strip().upper()
    if sym in _SYMBOL_TO_SLUG:
        slug = _SYMBOL_TO_SLUG[sym]
    elif company_name:
        slug = clean_company_slug(company_name)
    else:
        slug = sym.lower()
    return f"https://groww.in/charts/stocks/{slug}?exchange=NSE"

def get_company_name(symbol: str) -> str:
    _load_registry()
    return _SYMBOL_TO_COMPANY.get((symbol or "").strip().upper(), symbol)
