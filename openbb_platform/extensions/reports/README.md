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

### yfinance
- **Usage:** Market data (indices, currencies, commodities, VIX), undervalued large caps, and charts.
- **API Key:** Not required.

### federal_reserve
- **Usage:** Treasury yields.
- **API Key:** Not required.

### Financial Modeling Prep (FMP)
- **Usage:** Economic calendar.
- **Sign-up:** Get a free API key from [https://site.financialmodelingprep.com/developer/docs/](https://site.financialmodelingprep.com/developer/docs/).
- **Authentication:** The API key is passed as a query parameter `&apikey=YOUR_API_KEY`.
- **Free Tier:** The free tier provides access to a wide range of data, including the economic calendar.

### Benzinga
- **Usage:** Top market news.
- **API Key:** Required.

### Setting API Keys
To set your API keys, you can either set them as environment variables or use the OpenBB Hub.
Example environment variables:
```bash
export OPENBB_FMP_API_KEY="YOUR_KEY"
export OPENBB_BENZINGA_API_KEY="YOUR_KEY"
```
Please refer to the main OpenBB Platform documentation for more details on setting up credentials.

## Customization

You can customize the report by editing the `reports_api.py` file. For example, you can add or remove tickers from the `indices`, `currencies`, and `commodities` dictionaries to track different assets. You can also modify the `investment_report.html` template to change the layout and styling of the report.
