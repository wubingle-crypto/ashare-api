"""
A-Share Stock Data API - Free real-time & historical data for Chinese stocks.

Powered by binglewu (Hermes Agent)
Donation: 0x19979a2498867a1bC0F823Fd309B05eEe8Bc5624 (BSC/BEP-20)
"""

import re
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── App Setup ──────────────────────────────────────────────────────────

DONATION_ADDR = "0x19979a2498867a1bC0F823Fd309B05eEe8Bc5624"
DONATION_NETWORK = "BSC (BEP-20)"

app = FastAPI(
    title="A-Share Stock Data API",
    description="Free real-time and historical A-share stock data. Built for quants.",
    version="1.0.0",
    contact={
        "name": "binglewu",
        "url": "https://github.com/wubingle-crypto/ashare-quant-toolkit",
    },
)

# Allow all origins (public API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ────────────────────────────────────────────────────────────

def _add_donation_headers(resp: JSONResponse):
    """Add donation info to response headers."""
    resp.headers["X-Donation-Address"] = DONATION_ADDR
    resp.headers["X-Donation-Network"] = DONATION_NETWORK
    resp.headers["X-Powered-By"] = "Hermes Agent + binglewu"
    return resp


def _code_to_tencent(code: str) -> str:
    """Convert stock code to Tencent format (sh600519 / sz000001)."""
    code = code.strip()
    # Already has prefix
    if re.match(r'^(sh|sz|SH|SZ)\d{6}$', code):
        return code[:2].lower() + code[2:]
    # Pure 6-digit code
    if re.match(r'^\d{6}$', code):
        if code.startswith(("60", "68")):
            return f"sh{code}"
        return f"sz{code}"
    # Fallback
    return code


def _decode_gbk(data: bytes) -> str:
    """Try to decode bytes, handling GBK encoding."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("gbk")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")


def _fetch_tencent_quote(tencent_code: str) -> dict:
    """Fetch a single quote from Tencent Finance API."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://qt.gtimg.cn/q={tencent_code}", "--max-time", "8"],
            capture_output=True,
            timeout=10,
        )
        raw = _decode_gbk(result.stdout)
        # Parse: v_sh600519="field1~field2~...";
        match_full = re.search(r'^[^=]+="(.+)";?\s*$', raw, re.MULTILINE)
        if not match_full:
            return {"error": "parse_failed", "raw": raw[:500]}
        fields = match_full.group(1).split("~")
        # Field mapping for Tencent format
        # https://www.qt.gtimg.cn/q=sh600519
        # 0:market, 1:name, 2:code, 3:price, 4:prev_close, 5:open, 6:volume, 
        # 7:buy_vol, 8:sell_vol, 9:bid_price, ... 29:datetime, 30:change, 31:change_pct
        try:
            price = float(fields[3]) if fields[3] else 0
            prev_close = float(fields[4]) if fields[4] else 0
            open_price = float(fields[5]) if fields[5] else 0
            high = float(fields[33]) if len(fields) > 33 and fields[33] else price
            low = float(fields[34]) if len(fields) > 34 and fields[34] else price
            volume = int(fields[6]) if fields[6] else 0
            amount = float(fields[37]) if len(fields) > 37 and fields[37] else 0
            change = float(fields[31]) if len(fields) > 31 and fields[31] else 0
            change_pct = float(fields[32]) if len(fields) > 32 and fields[32] else 0
            turnover = float(fields[38]) / 100 if len(fields) > 38 and fields[38] else 0
        except (ValueError, IndexError):
            return {"error": "parse_failed", "raw": raw[:500]}
        
        return {
            "code": fields[2],
            "name": fields[1],
            "market": fields[0],
            "price": price,
            "prev_close": prev_close,
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "change": change,
            "change_pct": change_pct,
            "turnover_pct": turnover,
            "datetime": fields[30] if len(fields) > 30 else "",
        }
    except Exception as e:
        return {"error": str(e)}


def _fetch_batch_tencent(codes: list) -> dict:
    """Fetch multiple quotes in one request."""
    tencent_codes = [_code_to_tencent(c) for c in codes]
    query = ",".join(tencent_codes)
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://qt.gtimg.cn/q={query}", "--max-time", "10"],
            capture_output=True,
            timeout=15,
        )
        raw = _decode_gbk(result.stdout)
        
        data = {}
        for line in raw.strip().split("\n"):
            if "=" not in line:
                continue
            match = re.search(r'^[^=]+="(.+)"\s*$', line.strip())
            if match:
                fields = match.group(1).split("~")
                code = fields[2] if len(fields) > 2 else "unknown"
                try:
                    price = float(fields[3]) if fields[3] else 0
                except:
                    price = 0
                data[code] = {
                    "code": code,
                    "name": fields[1] if len(fields) > 1 else "",
                    "price": price,
                    "change_pct": float(fields[32]) / 100 if len(fields) > 32 and fields[32] else 0,
                }
        return data
    except Exception as e:
        return {"error": str(e)}


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """API root with documentation links."""
    resp = JSONResponse({
        "name": "A-Share Stock Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "/quote/{code}": "Get real-time stock quote",
            "/history/{code}": "Get historical daily data",
            "/batch": "Batch quotes (POST)",
            "/market": "Major indices snapshot",
            "/search": "Search stocks",
        },
        "donation": {
            "address": DONATION_ADDR,
            "network": DONATION_NETWORK,
        },
        "powered_by": "Hermes Agent + binglewu",
    })
    return _add_donation_headers(resp)


@app.get("/quote/{code}")
async def get_quote(code: str):
    """Get real-time quote for a single stock.
    
    Examples:
      - /quote/600519    (贵州茅台)
      - /quote/000001    (平安银行)
      - /quote/300750    (宁德时代)
    """
    tencent_code = _code_to_tencent(code)
    data = _fetch_tencent_quote(tencent_code)
    
    resp = JSONResponse({
        "status": "ok" if "error" not in data else "error",
        "data": data,
        "donation": {
            "address": DONATION_ADDR,
            "network": DONATION_NETWORK,
        },
    })
    return _add_donation_headers(resp)


@app.get("/history/{code}")
async def get_history(
    code: str,
    start: Optional[str] = Query(None, description="Start date YYYYMMDD"),
    end: Optional[str] = Query(None, description="End date YYYYMMDD"),
    adjust: Optional[str] = Query(None, description="Adjust: '' (none), 'qfq' (forward), 'hfq' (backward)"),
):
    """Get historical daily data for a stock.
    
    Uses akshare (Tushare-based) for accurate historical data.
    """
    end_date = end or datetime.now().strftime("%Y%m%d")
    start_date = start or (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    adjust = adjust or ""
    
    try:
        # akshare needs market prefix: sz000001, sh600519
        tc = _code_to_tencent(code)  # returns 'sh600519' format
        df = ak.stock_zh_a_hist_tx(
            symbol=tc,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        records = df.to_dict(orient="records")
        # Convert dates to string
        for r in records:
            for k, v in r.items():
                if hasattr(v, "strftime"):
                    r[k] = v.strftime("%Y-%m-%d")
        
        resp = JSONResponse({
            "status": "ok",
            "count": len(records),
            "data": records,
            "donation": {
                "address": DONATION_ADDR,
                "network": DONATION_NETWORK,
            },
        })
        return _add_donation_headers(resp)
    except Exception as e:
        resp = JSONResponse({
            "status": "error",
            "error": str(e),
            "donation": {
                "address": DONATION_ADDR,
                "network": DONATION_NETWORK,
            },
        })
        return _add_donation_headers(resp)


@app.post("/batch")
async def batch_quote(codes: list[str] = Query(..., description="Stock codes, e.g. ['600519','000001','300750']")):
    """Get quotes for multiple stocks in one request.
    
    POST JSON body: {"codes": ["600519", "000001", "300750"]}
    or query param: /batch?codes=600519&codes=000001
    """
    if isinstance(codes, str):
        codes = [codes]
    data = _fetch_batch_tencent(codes)
    
    resp = JSONResponse({
        "status": "ok" if "error" not in data else "error",
        "data": data,
        "donation": {
            "address": DONATION_ADDR,
            "network": DONATION_NETWORK,
        },
    })
    return _add_donation_headers(resp)


@app.get("/market")
async def market_snapshot():
    """Get snapshot of major indices."""
    indices = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000688": "科创板指",
    }
    data = _fetch_batch_tencent(list(indices.keys()))
    
    resp = JSONResponse({
        "status": "ok",
        "data": data,
        "donation": {
            "address": DONATION_ADDR,
            "network": DONATION_NETWORK,
        },
    })
    return _add_donation_headers(resp)


@app.get("/search")
async def search_stock(q: str = Query(..., description="Search keyword (name or code)")):
    """Search stocks by name or code."""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        # Filter by name or code
        mask = df["代码"].str.contains(q, case=False) | df["名称"].str.contains(q, case=False)
        results = df[mask].head(20).to_dict(orient="records")
        
        resp = JSONResponse({
            "status": "ok",
            "count": len(results),
            "data": results,
            "donation": {
                "address": DONATION_ADDR,
                "network": DONATION_NETWORK,
            },
        })
        return _add_donation_headers(resp)
    except Exception as e:
        resp = JSONResponse({
            "status": "error",
            "error": str(e),
        })
        return _add_donation_headers(resp)


# ── Startup Hook ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7800)
