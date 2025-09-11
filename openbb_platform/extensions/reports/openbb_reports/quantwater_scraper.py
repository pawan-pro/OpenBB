"""
Quantwater Scraper for Economic Events.

This module provides a scraper for fetching economic events from the Quantwater Tech Investments blog.
The scraper is designed to be robust to minor changes in the blog's structure and timing of posts.

**Scraping Strategy:**

1.  **URL Discovery:** The scraper attempts to find the current week's economic calendar
    by checking for blog posts published on Monday, Sunday, and Tuesday of the current week.
    The URL format is assumed to be `https://quantwatertech.netlify.app/blogs/YYYY-MM-DD`.

2.  **HTML Parsing:** The scraper uses BeautifulSoup to parse the HTML of the blog post.
    It looks for `div` elements with the class `event-card` to identify individual events.
    Within each event card, it extracts data from elements with specific class names
    (e.g., `event-date`, `event-time`, `event-currency`, etc.).

3.  **Data Filtering:** The scraper filters for events with an importance of 3 (High impact).

4.  **Caching:** The scraped data is cached in a JSON file for one week to minimize
    redundant requests and improve performance. The cache is invalidated automatically
    after 7 days.

**Assumed HTML Structure:**

The scraper assumes the following HTML structure for each event card:

```html
<div class="event-card">
    <p class="event-date">YYYY-MM-DD</p>
    <p class="event-time">HH:MM</p>
    <p class="event-currency">CUR</p>
    <p class="event-name">Event Name</p>
    <p class="event-forecast">...</p>
    <p class="event-previous">...</p>
    <p class="event-importance">3/3</p>
    <p class="event-notes">...</p>
</div>
```

If the blog's HTML structure changes significantly, this scraper may need to be updated.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd
import requests
from bs4 import BeautifulSoup


@dataclass
class EconomicEvent:
    """A dataclass to hold economic event data."""

    date: str
    time_ist: str
    currency: str
    event_name: str
    forecast: str
    previous: str
    importance: int
    notes: Optional[str] = None


class QuantwaterScraper:
    """
    A scraper for fetching economic events from Quantwater Tech Investments blog.

    This scraper is designed to find the latest weekly economic calendar post,
    parse the event data, and return it as a list of EconomicEvent objects.
    It includes caching to avoid redundant requests.
    """

    def __init__(self, cache_dir: Path = Path("cache")):
        """
        Initializes the QuantwaterScraper.

        Parameters
        ----------
        cache_dir : Path, optional
            The directory to store cache files, by default Path("cache")
        """
        self.base_url = "https://quantwatertech.netlify.app/blogs/"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get_events(self) -> Optional[pd.DataFrame]:
        """
        Public method to get economic events.

        This method orchestrates the process of fetching events, including
        checking the cache, discovering the blog URL, scraping the data, and
        updating the cache.

        Returns
        -------
        Optional[pd.DataFrame]
            A DataFrame of high-importance economic events, or None if an error occurs.
        """
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        cache_path = self._get_cache_path(week_start)

        # Try to read from cache first
        cached_events = self._read_from_cache(cache_path)
        if cached_events:
            df = pd.DataFrame([asdict(e) for e in cached_events])
            return df

        # If cache is not available, scrape from the web
        blog_url = self._discover_blog_url(week_start)
        if not blog_url:
            print("Could not find the economic calendar blog for the current week.")
            return None

        events = self._scrape_events_from_url(blog_url)
        if events:
            self._write_to_cache(cache_path, events)
            df = pd.DataFrame([asdict(e) for e in events])
            return df

        return None

    def _get_cache_path(self, week_start: datetime) -> Path:
        """
        Gets the cache file path for a given week.

        Parameters
        ----------
        week_start : datetime
            The start date of the week.

        Returns
        -------
        Path
            The path to the cache file.
        """
        return self.cache_dir / f"quantwater_events_{week_start.strftime('%Y-%U')}.json"

    def _read_from_cache(self, cache_path: Path) -> Optional[List[EconomicEvent]]:
        """
        Reads event data from a cache file.

        The cache is considered valid for 7 days.

        Parameters
        ----------
        cache_path : Path
            The path to the cache file.

        Returns
        -------
        Optional[List[EconomicEvent]]
            A list of EconomicEvent objects, or None if the cache is invalid or expired.
        """
        if not cache_path.exists():
            return None

        # Check if the cache is older than a week
        file_mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_mod_time > timedelta(days=7):
            return None

        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return [EconomicEvent(**item) for item in data]
            except (json.JSONDecodeError, TypeError):
                return None

    def _write_to_cache(self, cache_path: Path, events: List[EconomicEvent]):
        """
        Writes event data to a cache file.

        Parameters
        ----------
        cache_path : Path
            The path to the cache file.
        events : List[EconomicEvent]
            The list of EconomicEvent objects to cache.
        """
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in events], f, indent=4)

    def _discover_blog_url(self, week_start: datetime) -> Optional[str]:
        """
        Discovers the URL for the current week's economic calendar blog post.
        It tries Monday, Sunday, and Tuesday of the week.

        Parameters
        ----------
        week_start : datetime
            The start date of the week.

        Returns
        -------
        Optional[str]
            The URL of the blog post, or None if not found.
        """
        headers = {"User-Agent": "Lynx"}
        # Monday is 0 and Sunday is 6. Let's find the Monday of the week.
        monday = week_start - timedelta(days=week_start.weekday())

        # Order to check: Monday, Sunday (of the previous week), Tuesday
        dates_to_check = [
            monday,
            monday - timedelta(days=1),  # Sunday
            monday + timedelta(days=1),  # Tuesday
        ]

        for date in dates_to_check:
            url = f"{self.base_url}{date.strftime('%Y-%m-%d')}"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return url
            except requests.RequestException:
                continue
        return None

    def _scrape_events_from_url(self, url: str) -> Optional[List[EconomicEvent]]:
        """
        Scrapes economic events from a given URL.

        Parameters
        ----------
        url : str
            The URL of the blog post to scrape.

        Returns
        -------
        Optional[List[EconomicEvent]]
            A list of EconomicEvent objects, or None if an error occurs.
        """
        try:
            headers = {"User-Agent": "Lynx"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            event_cards = soup.find_all("div", class_="event-card")
            if not event_cards:
                # Fallback: try to find cards with a similar pattern if the class name is wrong
                event_cards = soup.select('div[class*="event-card"]')

            events = []
            for card in event_cards:
                event = self._parse_event_card(card)
                if event and event.importance == 3:
                    events.append(event)

            return events
        except (requests.RequestException, Exception) as e:
            print(f"Error scraping events from {url}: {e}")
            return None

    def _parse_event_card(self, card) -> Optional[EconomicEvent]:
        """
        Parses a single event card element to extract event details.

        This is a best-effort parser based on a presumed HTML structure.
        It looks for specific class names within the event card.

        Parameters
        ----------
        card : Tag
            The BeautifulSoup tag representing the event card.

        Returns
        -------
        Optional[EconomicEvent]
            An EconomicEvent object, or None if parsing fails.
        """
        try:
            date = card.find(class_="event-date").text.strip()
            time_ist = card.find(class_="event-time").text.strip()
            currency = card.find(class_="event-currency").text.strip()
            event_name = card.find(class_="event-name").text.strip()

            forecast_tag = card.find(class_="event-forecast")
            forecast = forecast_tag.text.strip() if forecast_tag else "N/A"

            previous_tag = card.find(class_="event-previous")
            previous = previous_tag.text.strip() if previous_tag else "N/A"

            importance_tag = card.find(class_="event-importance")
            importance_text = importance_tag.text.strip() if importance_tag else "0"
            importance = int(importance_text.split("/")[0])  # Assuming format "3/3"

            notes_tag = card.find(class_="event-notes")
            notes = notes_tag.text.strip() if notes_tag else None

            # Data validation and cleaning
            if not all([date, time_ist, currency, event_name]):
                return None

            return EconomicEvent(
                date=date,
                time_ist=time_ist,
                currency=currency,
                event_name=event_name,
                forecast=forecast,
                previous=previous,
                importance=importance,
                notes=notes,
            )
        except (AttributeError, ValueError, IndexError):
            # This can happen if a card has a different structure or is missing data.
            # print(f"Skipping a card due to parsing error: {e}")
            return None


def test_scraper():
    """
    A simple function to test the QuantwaterScraper.
    """
    print("--- Testing Quantwater Scraper ---")
    # Initialize scraper
    scraper = QuantwaterScraper()

    # To ensure we are not using cache for the test, we can clear it
    # For the purpose of this test, let's create a temporary cache dir
    test_cache_dir = Path("test_cache")
    scraper.cache_dir = test_cache_dir
    scraper.cache_dir.mkdir(exist_ok=True)

    print("Attempting to scrape events for the current week...")
    events_df = scraper.get_events()

    if events_df is not None and not events_df.empty:
        print("\n✅ Successfully scraped events!")
        print(f"Found {len(events_df)} high-importance events.")
        print("--- First 5 Events ---")
        print(events_df.head())
        print("----------------------")
    else:
        print("\n❌ Could not scrape events.")
        print("This could be because:")
        print("1. No blog post was found for the current week (Monday, Sunday, or Tuesday).")
        print("2. The website structure has changed, and the scraper needs to be updated.")
        print("3. There was a network error.")

    # Clean up the test cache directory
    import shutil
    shutil.rmtree(test_cache_dir)
    print("\n--- Test Complete ---")


if __name__ == "__main__":
    test_scraper()
