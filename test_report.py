import webbrowser
from pathlib import Path
from openbb import obb

def test_generate_daily_report():
    """Test the generate_daily_report function."""
    file_path = "daily_investment_report.html"

    # Ensure the file doesn't exist before running the test
    if Path(file_path).exists():
        Path(file_path).unlink()

    # Generate the report
    obb.reports.daily(file_path=file_path)

    # Check if the file was created
    assert Path(file_path).exists(), f"Report file was not created at {file_path}"

    print(f"Report generated successfully at {file_path}")

    # Open the report in the browser
    webbrowser.open(f"file://{Path(file_path).resolve()}")
    print("Opening the report in the browser...")
    print("Please check your browser to see the generated report.")
    print("If the report looks good, you can approve the changes.")

if __name__ == "__main__":
    test_generate_daily_report()
