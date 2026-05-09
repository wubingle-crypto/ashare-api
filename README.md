# A-Share Stock Data API

**Free, real-time Chinese A-share stock market data API.** Built for quants, traders, and developers.

## 🌐 API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /quote/{code}` | Real-time stock quote | `/quote/600519` |
| `GET /history/{code}` | Historical daily data | `/history/600519?start=20250101` |
| `POST /batch` | Batch quotes | `POST {"codes":["600519","000001"]}` |
| `GET /market` | Major indices snapshot | `/market` |
| `GET /search?q=` | Search stocks | `/search?q=茅台` |
| `GET /docs` | Interactive API docs | `/docs` |

### Quick Start

```bash
# Real-time quote for 贵州茅台
curl https://ashare.binglewu.workers.dev/quote/600519

# Historical data for 平安银行
curl "https://ashare.binglewu.workers.dev/history/000001?start=20250101"

# Market indices
curl https://ashare.binglewu.workers.dev/market
```

### Response Format

All responses include donation info in **headers**:

```json
{
  "status": "ok",
  "data": {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1372.99,
    "change_pct": 0.14,
    ...
  }
}
```

Every response also includes headers:
- `X-Donation-Address` — BSC wallet address
- `X-Donation-Network` — BSC (BEP-20)

## 💰 Support the Project

If you find this API useful, consider donating:

| Network | Address |
|---------|---------|
| **BSC (BEP-20)** | `0x19979a2498867a1bC0F823Fd309B05eEe8Bc5624` |

Your support keeps the servers running and the data flowing! 🚀

## 📦 Self-Hosting

```bash
git clone https://github.com/wubingle-crypto/ashare-api.git
cd ashare-api
pip install -r requirements.txt
python main.py
```

The API runs on port 7800 by default.

## ⚠️ Disclaimer

This is a free, unofficial API for educational and research purposes. Data is sourced from public Chinese financial data providers. Not for commercial trading decisions.

## 🔗 Related

- [ashare-quant-toolkit](https://github.com/wubingle-crypto/ashare-quant-toolkit) — Python quant toolkit with 5+ trading strategies
- [bwh-hermes-agent](https://github.com/wubingle-crypto/bwh-hermes-agent) — AI agent with Hermes integration

---

*Built with ❤️ by [binglewu](https://github.com/wubingle-crypto)*
