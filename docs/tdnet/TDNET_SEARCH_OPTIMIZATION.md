# TDnet Search Optimization Guide

## Overview
This document consolidates search strategies for the TDnet scraper to achieve >95% precision in identifying "Third-Party Allotment" (第三者割当) announcements. It replaces previous scattered guides on search terms and operators.

## 1. Optimal Search Queries

### Recommended Production Query
This query filters out noise (corrections, completions, exercise of rights) while capturing new issuances.

```text
"第三者割当" -払込完了 -訂正 -行使 -結果 -に関するお知らせ等
```

### Search Tiers
| Tier | Query | Purpose | Precision | Recall |
|------|-------|---------|-----------|--------|
| **1** | `第三者割当 発行に関するお知らせ` OR `第三者割当 募集に関するお知らせ` | Specific initial issuance/offering announcements. | High (95%+) | Medium (~90%) |
| **2** | `第三者割当 新株式 -払込完了` OR `第三者割当 新株予約権 -払込完了` | Common stock/warrant issuances (excluding completions). | High (90%+) | High (~98%) |
| **3** | `第三者割当 割当先決定` | Allottee decision announcements. | Medium (85%+) | High (100%) |

## 2. Search Operators (TDnet Specifics)

TDnet's search engine behaves differently from standard engines:

*   **AND Operator**: Space (` `). Example: `A B` finds documents containing both A and B.
*   **NOT Operator**: Minus (`-`). Example: `A -B` finds documents containing A but NOT B.
    *   *Critical*: Ensure there is a space before the minus sign.
*   **OR Operator**: Not natively supported in a single string in some contexts, but can be simulated by running multiple scrapes.

## 3. Keyword Analysis

### Positive Keywords (Include)
*   **第三者割当** (Third-Party Allotment): The core term.
*   **発行** (Issuance): Often accompanies new stock issuance.
*   **募集** (Offering): Used in "Issuance of shares for subscription".

### Negative Keywords (Exclude)
*   **払込完了** (Payment Completed): Post-deal status updates.
*   **行使** (Exercise): Refers to the exercise of warrants/stock options, not the initial allotment.
*   **訂正** (Correction): Corrections to previous documents (unless tracking diffs is required).
*   **結果** (Result): Often "Result of exercise".

## 4. Implementation Strategy

To maximize recall while maintaining precision, the scraper implements a "Tiered Filtering" approach:

1.  **Broad Search**: Query `第三者割当` to get a candidate list.
2.  **Negative Filter**: Programmatically exclude titles containing "払込完了", "訂正", etc., if the search engine limit is reached.
3.  **Content Verification**: (Enhanced Scraper) Download PDF and regex match for "割当先" (Allottee) to confirm it is a valid allotment document.

## 5. Usage Examples

### Basic Search
```python
from datetime import date
from src.services.tdnet import TdnetSearchScraper

scraper = TdnetSearchScraper()
result = scraper.scrape(start_date=date.today(), end_date=date.today())

print(f"Found {result.total_count} entries")
for entry in result.entries:
    print(f"{entry.publish_date}: {entry.title}")
```

### Enhanced Analysis (with PDF download)
```python
from datetime import date
from src.services.tdnet import TdnetSearchScraper

# Enable PDF download to extract deal details
scraper = TdnetSearchScraper(download_pdfs=True, output_dir="./data/pdfs")
result = scraper.scrape(start_date=date.today(), end_date=date.today())

for entry in result.entries:
    if entry.deal_size:
        print(f"Deal: {entry.company_name} - {entry.deal_size} {entry.deal_size_currency}")
```

### Using Helper Functions Directly
```python
from src.services.tdnet.tdnet_search_helpers import (
    extract_deal_details,
    parse_date_str,
)

# Parse a date string
d = parse_date_str("2026/01/15")  # Returns date(2026, 1, 15)

# Extract deal details from PDF text
details = extract_deal_details(pdf_text)
print(f"Investor: {details.get('investor')}")
print(f"Deal Size: {details.get('deal_size')}")
```

