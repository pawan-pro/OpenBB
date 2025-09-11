import base64
import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
import pandas as pd
import requests
from jinja2 import Environment, FileSystemLoader

from .quantwater_scraper import QuantwaterScraper

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def get_data_safely(func, **kwargs):
    """Safely retrieve data, handling exceptions."""
    try:
        result = func(**kwargs)
        if hasattr(result, 'to_df'):
            return result.to_df()
        return result
    except Exception as e:
        print(f"Could not retrieve data for {func.__name__} with args {kwargs}: {e}")
        return None


def generate_chart_base64(df, title, x_col, y_col):
    """Generates a line chart and returns it as a base64 encoded string."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df[y_col])
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def get_economic_events_fmp(
    start_date: str, end_date: str, country: str = "US", impact: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Get upcoming economic events from FMP.

    Parameters
    ----------
    start_date : str
        The start date of the events.
    end_date : str
        The end date of the events.
    country : str, optional
        The country to filter events by, by default "US"
    impact : Optional[str], optional
        The impact level to filter events by, by default None

    Returns
    -------
    Optional[pd.DataFrame]
        A DataFrame of economic events, or None if an error occurs.
    """
    try:
        api_key = os.environ.get("OPENBB_FMP_API_KEY")
        if not api_key:
            print("FMP API key not found. Please set it as an environment variable OPENBB_FMP_API_KEY.")
            return None

        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={start_date}&to={end_date}&apikey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        if country:
            df = df[df["country"].isin(country.split(","))]

        if impact:
            df = df[df["impact"].str.lower() == impact.lower()]

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching economic events from FMP: {e}")
        return None


def generate_daily_report(file_path: str = "daily_investment_report.html"):
    """
    Generates a daily investment report in HTML format.

    Parameters
    ----------
    file_path : str, optional
        The path to save the generated HTML report, by default "daily_investment_report.html"
    """
    from openbb import obb

    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)  # a bit more to be safe
    from_date = (end_date - timedelta(days=3)).strftime("%Y-%m-%d")
    to_date = (end_date + timedelta(days=3)).strftime("%Y-%m-%d")

    # 1. Daily Market Snapshot
    market_snapshot = {}
    # To add more assets, simply add new entries to the dictionaries below.
    # Make sure the ticker is compatible with the selected provider (yfinance in this case).
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "FTSE 100": "^FTSE",
        "DAX": "^GDAXI",
    }
    indices_data = {}
    for name, symbol in indices.items():
        df = get_data_safely(
            obb.index.price.historical,
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            provider="yfinance",
        )
        if df is not None and not df.empty:
            df["change"] = df["close"].diff()
            df["percent_change"] = (df["change"] / df["close"].shift(1)) * 100
            indices_data[name] = df.iloc[-1]
    market_snapshot["indices"] = indices_data

    currencies = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
    }
    currencies_data = {}
    for name, symbol in currencies.items():
        df = get_data_safely(
            obb.currency.price.historical,
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            provider="yfinance",
        )
        if df is not None and not df.empty:
            df["change"] = df["close"].diff()
            df["percent_change"] = (df["change"] / df["close"].shift(1)) * 100
            currencies_data[name] = df.iloc[-1]
    market_snapshot["currencies"] = currencies_data

    treasury_yields = {}
    df_treasury = get_data_safely(
        obb.fixedincome.government.treasury_rates, provider="federal_reserve"
    )
    if df_treasury is not None and not df_treasury.empty:
        last_yields = df_treasury.iloc[-1]
        treasury_yields["10-Year"] = {"rate": last_yields.get("year_10")}
        treasury_yields["2-Year"] = {"rate": last_yields.get("year_2")}
    market_snapshot["treasury_yields"] = treasury_yields

    commodities = {
        "Gold": "GC=F",
        "Silver": "SI=F",
        "WTI Crude Oil": "CL=F",
    }
    commodities_data = {}
    for name, symbol in commodities.items():
        df = get_data_safely(
            obb.derivatives.futures.historical,
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            provider="yfinance",
        )
        if df is not None and not df.empty:
            df["change"] = df["close"].diff()
            df["percent_change"] = (df["change"] / df["close"].shift(1)) * 100
            commodities_data[name] = df.iloc[-1]
    market_snapshot["commodities"] = commodities_data

    vix_df = get_data_safely(
        obb.index.price.historical,
        symbol="^VIX",
        start_date=start_date.strftime("%Y-%m-%d"),
        provider="yfinance",
    )
    if vix_df is not None and not vix_df.empty:
        vix_df["change"] = vix_df["close"].diff()
        market_snapshot["vix"] = vix_df.iloc[-1]

    # 2. Upcoming Economic Events
    economic_events_source = "Not available"
    scraper = QuantwaterScraper()
    economic_events = scraper.get_events()
    if economic_events is not None and not economic_events.empty:
        economic_events_source = "Quantwater"
        economic_events = economic_events.to_dict(orient="records")
    else:
        print("Quantwater scrape failed, falling back to FMP.")
        economic_events = get_economic_events_fmp(from_date, to_date, country="US,CA,GB,DE,FR,IT,JP,CN,IN")
        if economic_events is not None and not economic_events.empty:
            economic_events_source = "FMP"
            economic_events = economic_events.to_dict(orient="records")

    # 3. Undervalued Large Caps
    undervalued_large_caps = get_data_safely(
        obb.equity.discovery.undervalued_large_caps, provider="yfinance"
    )

    # 4. Top Market News
    top_news = get_data_safely(obb.news.world, limit=10, provider="benzinga")

    # 5. Key Charts
    charts = {"sp500": {}, "vix": {}}
    timeframes = {"1-Month": 30, "YTD": "YTD"}

    for tf_name, tf_days in timeframes.items():
        if tf_days == "YTD":
            start_date_tf = datetime(end_date.year, 1, 1).strftime("%Y-%m-%d")
        else:
            start_date_tf = (end_date - timedelta(days=tf_days)).strftime("%Y-%m-%d")

        sp500_df = get_data_safely(
            obb.index.price.historical,
            symbol="^GSPC",
            start_date=start_date_tf,
            provider="yfinance",
        )
        if sp500_df is not None and not sp500_df.empty:
            charts["sp500"][tf_name] = generate_chart_base64(
                sp500_df, f"S&P 500 - {tf_name}", "Date", "close"
            )

        vix_chart_df = get_data_safely(
            obb.index.price.historical,
            symbol="^VIX",
            start_date=start_date_tf,
            provider="yfinance",
        )
        if vix_chart_df is not None and not vix_chart_df.empty:
            charts["vix"][tf_name] = generate_chart_base64(
                vix_chart_df, f"VIX - {tf_name}", "Date", "close"
            )

    data = {
        "market_snapshot": market_snapshot,
        "economic_events": economic_events,
        "economic_events_source": economic_events_source,
        "undervalued_large_caps": undervalued_large_caps,
        "top_news": top_news,
        "charts": charts,
        "report_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Render the HTML report
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("investment_report.html")
    html_out = template.render(data=data, title="Daily Investment Report")

    # Save the report
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Report saved to {file_path}")
