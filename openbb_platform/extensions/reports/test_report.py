from datetime import datetime, timedelta
from openbb_reports.reports_api import get_economic_events_fmp

def test_get_economic_events():
    """Test the get_economic_events_fmp function."""
    from_date = datetime.now().strftime("%Y-%m-%d")
    to_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    print(f"Fetching economic events from {from_date} to {to_date} for the US...")

    events = get_economic_events_fmp(from_date, to_date, country="US")

    if events is not None and not events.empty:
        print("Top 5 upcoming events for the US:")
        print(events.head(5))
    elif events is not None:
        print("No upcoming events found for the US in the next 3 days.")
    else:
        print("Failed to fetch economic events.")

if __name__ == "__main__":
    test_get_economic_events()
