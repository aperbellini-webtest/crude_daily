import os
import smtplib
import ssl
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path.cwd()

def save_daily_chart(run_ts, ticker="BZ=F", daily_days=20, ma_window=5):
    daily = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=False)
    if daily.empty:
        raise ValueError("No daily data available")
    if isinstance(daily.columns, pd.MultiIndex):
        daily.columns = daily.columns.get_level_values(0)
    daily = daily.dropna().copy()
    if isinstance(daily["Close"], pd.DataFrame):
        daily["Close"] = daily["Close"].iloc[:, 0]
    daily = daily.tail(daily_days).copy()
    daily["Moving Average"] = daily["Close"].rolling(ma_window).mean()
    daily["Label"] = pd.to_datetime(daily.index).strftime("%Y-%m-%d")

    latest_price = float(daily["Close"].iloc[-1])
    latest_date = pd.to_datetime(daily.index[-1])

    csv_path = BASE_DIR / f"crude_daily_data_{run_ts}.csv"
    png_path = BASE_DIR / f"crude_daily_daily_{run_ts}.png"

    daily[["Close", "Moving Average"]].to_csv(csv_path, index_label="Date")

    x = range(len(daily))
    fig, ax = plt.subplots(figsize=(15, 7))
    bars = ax.bar(x, daily["Close"], color="#4C78A8", width=0.75, label="Daily Close")
    ax.plot(x, daily["Moving Average"], color="#F58518", marker="o", linewidth=2.5, label=f"{ma_window}-Day Moving Average")

    offset = daily["Close"].max() * 0.01
    for i, (bar, val) in enumerate(zip(bars, daily["Close"])):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset, f"${val:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title(f"Brent Crude Oil - Last {daily_days} Daily Quotes with Moving Average", fontsize=16, weight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("USD per barrel")
    ax.set_xticks(list(x))
    ax.set_xticklabels(daily["Label"], rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return latest_date, latest_price, csv_path, png_path

def save_intraday_chart(run_ts, ticker="BZ=F", period="5d", interval="1h", ma_window=5):
    intra = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if intra.empty:
        raise ValueError("No intraday data available")
    if isinstance(intra.columns, pd.MultiIndex):
        intra.columns = intra.columns.get_level_values(0)
    intra = intra.dropna().copy()
    if isinstance(intra["Close"], pd.DataFrame):
        intra["Close"] = intra["Close"].iloc[:, 0]
    intra["Moving Average"] = intra["Close"].rolling(ma_window).mean()
    intra = intra.tail(20).copy()
    intra["Label"] = pd.to_datetime(intra.index).strftime("%Y-%m-%d %H:%M")

    png_path = BASE_DIR / f"crude_daily_intraday_{run_ts}.png"

    x = range(len(intra))
    fig, ax = plt.subplots(figsize=(16, 7))
    bars = ax.bar(x, intra["Close"], color="#F28E2B", width=0.7, label="Close")
    ax.plot(x, intra["Moving Average"], color="#1F77B4", marker="o", linewidth=2.5, label=f"{ma_window}-Period Moving Average")

    offset = intra["Close"].max() * 0.01
    for i, (bar, val) in enumerate(zip(bars, intra["Close"])):
        ts = pd.to_datetime(intra.index[i])
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset, f"${val:.2f}\n{ts.strftime('%H:%M')}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Brent Crude Oil - Intraday Quotes with Moving Average", fontsize=16, weight="bold")
    ax.set_xlabel("Date and Time")
    ax.set_ylabel("USD per barrel")
    ax.set_xticks(list(x))
    ax.set_xticklabels(intra["Label"], rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return png_path

def send_email(subject, body, attachments):
    sender_email = os.environ["CRUDE_GMAIL_USER"]
    app_password = os.environ["CRUDE_GMAIL_APP_PASSWORD"]
    recipient_email = "aperbellini@gmail.com"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    for file_path in attachments:
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{Path(file_path).name}"')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=context)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

def main():
    run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    latest_date, latest_price, csv_path, daily_png = save_daily_chart(run_ts)
    intra_png = save_intraday_chart(run_ts)
    now_text = latest_date.strftime("%Y-%m-%d %H:%M")
    send_email("Brent update", f"aggiornamento brent / {now_text}", [daily_png, intra_png])
    print(f"Sent email with latest close {latest_price:.2f} USD/barrel")
    print(f"Saved: {csv_path}")
    print(f"Saved: {daily_png}")
    print(f"Saved: {intra_png}")

if __name__ == "__main__":
    main()
