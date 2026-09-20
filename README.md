# Project: Tra cứu giá công bố

Python project to search the DAV public portal for records tied to the declared unit "Vinphaco / Công ty cổ phần dược phẩm Vĩnh Phúc" and export matching results to Excel.

## Features
- Search by multiple equivalent keywords and aliases
- Normalizes variants with/without accents, spacing, underscores, punctuation, and uppercase/lowercase differences
- Supports multi-page crawling with delays and retry logic
- Exports results to `.xlsx`
- Writes a simple JSON summary report

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py \
  --keywords "Vinphaco" "Công ty cổ phần dược phẩm Vĩnh Phúc" \
  --output output/vinphaco_results.xlsx
```

Or use the default built-in aliases:

```bash
python main.py
```

## Output
- Excel file in `output/`
- Summary JSON file in `output/`
- Console log with record count and completion status

## Important note
This tool is designed for publicly accessible information and respects normal site usage. It includes retries, rate limiting, and consistent session headers to reduce the chance of being blocked. If the target site enforces CAPTCHA or bot protection, the script will stop gracefully and report the issue.
