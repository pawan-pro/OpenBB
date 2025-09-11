import base64
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from openbb import obb


def get_data_safely(func, **kwargs: Any) -> Optional[Any]:
    """Safely retrieve data, handling exceptions."""
    try:
        result = func(**kwargs)
        if hasattr(result, "to_df"):
            return result.to_df()
        return result
    except Exception:
        return None


def generate_chart_base64(df, title, x_col, y_col) -> str:
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


def get_market_snapshot(start_date: datetime) -> Dict:
    """Get the daily market snapshot."""
    market_snapshot: Dict[str, Any] = {}
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

    currencies = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"}
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

    commodities = {"Gold": "GC=F", "Silver": "SI=F", "WTI Crude Oil": "CL=F"}
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

    return market_snapshot


def get_economic_events() -> Optional[Any]:
    """Get upcoming economic events."""
    events = get_data_safely(
        obb.economy.calendar, provider="tradingeconomics", country="United States"
    )
    if events is None:
        print("Could not retrieve economic events from Trading Economics.")
    return events


def get_undervalued_large_caps() -> Optional[Any]:
    """Get undervalued large caps."""
    caps = get_data_safely(
        obb.equity.discovery.undervalued_large_caps, provider="yfinance"
    )
    if caps is None:
        print("Could not retrieve undervalued large caps from yfinance.")
    return caps


def get_top_news() -> Optional[Any]:
    """Get top market news."""
    news = get_data_safely(obb.news.world, limit=10, provider="biztoc")
    if news is None:
        print("Could not retrieve news from BizToc, trying MarketAux...")
        news = get_data_safely(obb.news.world, limit=10, provider="marketaux")
        if news is None:
            print("Could not retrieve news from MarketAux.")
    return news


def get_charts(end_date: datetime) -> Dict:
    """Get key charts."""
    charts: Dict[str, Any] = {"sp500": {}, "vix": {}}
    timeframes = {"1-Month": 30, "YTD": "YTD"}

    for tf_name, tf_days in timeframes.items():
        if tf_days == "YTD":
            start_date_tf = datetime(end_date.year, 1, 1).strftime("%Y-%m-%d")
        else:
            start_date_tf = (end_date - timedelta(days=int(tf_days))).strftime(
                "%Y-%m-%d"
            )

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
    return charts


def get_highlights(market_snapshot: Dict, undervalued_large_caps: Any) -> Dict:
    """Get highlights from the data."""
    highlights: Dict[str, Any] = {}

    # Top 3 gainers/losers
    if market_snapshot and market_snapshot.get("indices"):
        indices = market_snapshot["indices"]
        sorted_indices = sorted(
            indices.items(), key=lambda item: item[1]["percent_change"]
        )
        highlights["top_gainers"] = sorted_indices[-3:]
        highlights["top_losers"] = sorted_indices[:3]

    # Unusual volume
    if undervalued_large_caps is not None and not undervalued_large_caps.empty:
        unusual_volume = []
        for index, row in undervalued_large_caps.iterrows():
            historical_data = get_data_safely(
                obb.equity.price.historical,
                symbol=row["symbol"],
                start_date=(datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d"),
                provider="yfinance",
            )
            if historical_data is not None and not historical_data.empty:
                avg_volume = historical_data["volume"].rolling(window=20).mean().iloc[-1]
                if row["volume"] > 2 * avg_volume:
                    unusual_volume.append(row)
        highlights["unusual_volume"] = unusual_volume

    # New highs/lows
    if market_snapshot and market_snapshot.get("indices"):
        new_highs_lows: Dict[str, Any] = {"highs": [], "lows": []}
        for name, values in market_snapshot["indices"].items():
            historical_data = get_data_safely(
                obb.index.price.historical,
                symbol=values.name,
                start_date=(datetime.now() - timedelta(days=365)).strftime(
                    "%Y-%m-%d"
                ),
                provider="yfinance",
            )
            if historical_data is not None and not historical_data.empty:
                if values["close"] >= historical_data["high"].max():
                    new_highs_lows["highs"].append(name)
                if values["close"] <= historical_data["low"].min():
                    new_highs_lows["lows"].append(name)
        highlights["new_highs_lows"] = new_highs_lows

    return highlights


def generate_daily_report(file_path: str = "daily_investment_report.html"):
    """
    Generates a daily investment report in HTML format.

    Parameters
    ----------
    file_path : str, optional
        The path to save the generated HTML report, by default "daily_investment_report.html"
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)

    market_snapshot = get_market_snapshot(start_date)
    economic_events = get_economic_events()
    undervalued_large_caps = get_undervalued_large_caps()
    top_news = get_top_news()
    charts = get_charts(end_date)
    highlights = get_highlights(market_snapshot, undervalued_large_caps)

    data = {
        "market_snapshot": market_snapshot,
        "economic_events": economic_events,
        "undervalued_large_caps": undervalued_large_caps,
        "top_news": top_news,
        "charts": charts,
        "highlights": highlights,
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
