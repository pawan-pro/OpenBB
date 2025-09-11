# OpenBB Reports Extension

This extension provides functionality to generate a daily investment report in HTML format.

## Features

- **Modular Sections:** The report is divided into several sections, each focusing on a different aspect of the market.
- **Data Coverage:** It uses a variety of free data providers to maximize information coverage. If data for a section cannot be retrieved, the section will be clearly marked as "Data not available".
- **Highlights:** A summary of key market movements, including top gainers/losers, stocks with unusual volume, and new 52-week highs/lows.
- **Charts:** Visualizations of key market indices like the S&P 500 and VIX.

## How to Run the Report

The report can be generated using the `run_report.py` script from the command line.

Navigate to the `openbb_platform` directory and run the following command:

```bash
python -m extensions.reports.openbb_reports.run_report
```

This will generate a timestamped HTML file in the current directory (e.g., `daily_investment_report_20250910_172600.html`).

You can also specify a custom file path and name:

```bash
python -m extensions.reports.openbb_reports.run_report --file-path my_reports/today_report.html
```

## Data Providers and API Keys

The report uses the following data providers. Some of them require API keys to be set up in your OpenBB Platform environment.

- **yfinance:** Used for market data (indices, currencies, commodities, VIX), undervalued large caps, and charts. (No API key required)
- **federal_reserve:** Used for treasury yields. (No API key required)
- **tradingeconomics:** Used for the economic calendar. Requires an API key. You can get a free key from their website.
- **biztoc:** Used for top market news. Requires an API key from RapidAPI.
- **marketaux:** Used as a fallback for top market news. Requires an API key.

To set your API keys, you can either set them as environment variables or use the OpenBB Hub. Please refer to the main OpenBB Platform documentation for more details on setting up credentials.

## Customization

You can customize the report by editing the `reports_api.py` file. For example, you can add or remove tickers from the `indices`, `currencies`, and `commodities` dictionaries to track different assets. You can also modify the `investment_report.html` template to change the layout and styling of the report.
