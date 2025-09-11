import argparse
from datetime import datetime
from .reports_api import generate_daily_report, get_data_safely

def main():
    """Main function to run the daily report generation."""
    parser = argparse.ArgumentParser(description="Generate a daily investment report.")
    parser.add_argument(
        "--file-path",
        type=str,
        help="The path to save the generated HTML report.",
    )
    args = parser.parse_args()

    file_path = args.file_path
    if not file_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"daily_investment_report_{timestamp}.html"

    print(f"Generating report and saving to {file_path}...")

    # We can't directly check which sections have missing data without duplicating the logic
    # from generate_daily_report. Instead, we rely on the print statements inside the
    # data fetching functions in reports_api.py to inform the user about missing data.
    generate_daily_report(file_path)

    print("Report generation complete.")


if __name__ == "__main__":
    main()
