# Crude Daily

Automated Brent crude oil tracker with charts and email alerts.

## What it does

- Downloads Brent crude oil data.
- Creates a daily chart for the last 20 trading days.
- Creates an intraday chart with price labels and time.
- Sends the two charts by email.
- Saves outputs with timestamped filenames.

## Schedule

The workflow runs Monday to Friday at:
- 07:00
- 11:00
- 15:00
- 19:00

## Files generated

Each run creates files like:

- `crude_daily_data_YYYY-MM-DD_HH-MM-SS.csv`
- `crude_daily_daily_YYYY-MM-DD_HH-MM-SS.png`
- `crude_daily_intraday_YYYY-MM-DD_HH-MM-SS.png`

## Requirements

- Python 3.11+
- GitHub Actions
- Gmail App Password for SMTP email sending

## GitHub secrets

Set these repository secrets:

- `CRUDE_GMAIL_USER`
- `CRUDE_GMAIL_APP_PASSWORD`

## Workflow

The workflow is in:

`.github/workflows/crude_daily.yml`

## Notes

- Weekend runs are disabled.
- The script sends the latest charts to the configured email address.
- Outputs are also uploaded as GitHub Actions artifacts.

bacino sul pisello
