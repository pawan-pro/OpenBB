import base64
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader


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

    # 1. Daily Market Snapshot
    market_snapshot = {}
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
            obb.commodity.price.historical,
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
    economic_events = None

    # 3. Undervalued Large Caps
    undervalued_large_caps = get_data_safely(
        obb.equity.discovery.undervalued_large_caps, provider="yfinance"
    )

    # 4. Top Market News
    top_news = get_data_safely(obb.news.world, limit=10, provider="yfinance")

    # 5. Key Charts
    charts = {}
    chart_start_date = (end_date - timedelta(days=30)).strftime("%Y-%m-%d")

    sp500_df = get_data_safely(
        obb.index.price.historical,
        symbol="^GSPC",
        start_date=chart_start_date,
        provider="yfinance",
    )
    if sp500_df is not None and not sp500_df.empty:
        charts["sp500"] = generate_chart_base64(
            sp500_df, "S&P 500 - 30 Days", "Date", "close"
        )

    vix_chart_df = get_data_safely(
        obb.index.price.historical,
        symbol="^VIX",
        start_date=chart_start_date,
        provider="yfinance",
    )
    if vix_chart_df is not None and not vix_chart_df.empty:
        charts["vix"] = generate_chart_base64(
            vix_chart_df, "VIX - 30 Days", "Date", "close"
        )

    data = {
        "market_snapshot": market_snapshot,
        "economic_events": economic_events,
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
