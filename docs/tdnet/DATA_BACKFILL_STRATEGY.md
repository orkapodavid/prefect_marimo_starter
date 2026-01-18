# Data Backfill & PDF Retrieval Strategy

## Overview
TDnet only retains documents for **30 days**. This document outlines the strategy for backfilling historical data and retrieving PDFs that have expired from the public TDnet search, based on research into JPX and EDINET APIs.

## 1. The Retention Problem
*   **TDnet Public Search**: URLs `https://www.release.tdnet.info/inbs/{ID}.pdf` expire after 30 days.
*   **Impact**: Scrapers cannot rely on public URLs for historical analysis or long-term database building.

## 2. Implemented Strategy: TDnet Official Archive (Free)
This strategy is currently implemented in `src/tdnet/search_backfill.py`.

*   **Method**: Scrapes daily lists from `https://www.release.tdnet.info/inbs/I_list_001_{YYYYMMDD}.html`.
*   **Limitations**: Only works for recent data (~30 days).

## 3. Planned Strategy: JPX TDnet API (Official)
*   **Test Key**: `7u5o0oxk88aVKCpnttiux9TZQn5WyPGp3iVQSc6M`
*   **Capabilities**:
    *   `v1/documents`: List documents by date range.
    *   Returns permanent (or long-retention) download URLs.

### JSON Request Example
```json
{
  "accessKey": "{api_key}",
  "code": "12340", // Company Code
  "dateFrom": "2023-01-01",
  "dateTo": "2023-12-31"
}
```

## 4. Planned Strategy: EDINET API (Statutory/Free)
EDINET is the Japanese EDGAR. It holds statutory filings permanently.
*   **Match Rate**: ~40% of TDnet "Third-Party Allotment" announcements have a corresponding EDINET filing (Securities Registration Statement or Extraordinary Report).
*   **Cost**: Free.
*   **API Key**: Required (e.g., `974819df3abc42938825514c8a4ebfc9`).

### Workflow
1.  **Search**: Use `GET /api/v2/documents.json` with `date` parameter.
2.  **Filter**: Look for doc descriptions matching "Third-Party Allotment" or "Extraordinary Report".
3.  **Download**: `GET /api/v2/documents/{docID}?type=2` (PDF).

### Code Snippet (Python)
```python
import requests
def download_edinet_pdf(doc_id, api_key):
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
    params = {"type": 2, "Subscription-Key": api_key}
    res = requests.get(url, params=params)
    if res.status_code == 200:
        with open(f"{doc_id}.pdf", "wb") as f:
            f.write(res.content)
```

## 5. Hybrid Strategy Recommendation
1.  **Recent Data (<30 Days)**: Use `TDnetPDFBackfill` (TDnet Official Archive strategy).
2.  **Statutory/Major Deals**: Query EDINET API daily for permanent records (Planned).
3.  **Historical/Gap Filling**: Use JPX TDnet API (Paid/Contract) for complete backfill (Planned).
