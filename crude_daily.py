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
import logging
import sys

# Configurazione logging dettagliato
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/crude_debug.log')
    ]
)

BASE_DIR = Path.cwd()


def save_daily_chart(run_ts, ticker="BZ=F", daily_days=20, ma_window=5):
    """Scarica dati daily e crea grafico con istogrammi e moving average"""
    logging.info("=== INIZIO save_daily_chart ===")
    
    daily = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=False)
    if daily.empty:
        logging.error("No daily data available")
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
    
    logging.info(f"Ultimo prezzo daily: {latest_price:.2f} USD/barrel")
    logging.info(f"Data ultimo prezzo: {latest_date}")

    history_csv_path = BASE_DIR / "crude_daily_history.csv"
    png_path = BASE_DIR / f"crude_daily_daily_{run_ts}.png"

    # CSV EXPORT DETTAGLIATO con tutte le colonne
    daily_export = daily.reset_index().copy()
    daily_export["RunTimestamp"] = run_ts
    daily_export["Ticker"] = ticker

    if history_csv_path.exists():
        old_history = pd.read_csv(history_csv_path)
        combined = pd.concat([old_history, daily_export], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "Ticker"], keep="last").sort_values("Date")
    else:
        combined = daily_export

    # Salva CSV con tutte le colonne: Date, Open, High, Low, Close, Volume, Dividends, Stock Splits, MA5
    combined.to_csv(history_csv_path, index=False)
    logging.info(f"CSV storico salvato: {history_csv_path}")

    # CREAZIONE GRAFICO - CODICE ORIGINALE PERFETTO
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
    
    logging.info(f"Grafico daily salvato: {png_path}")
    logging.info("=== FINE save_daily_chart ===")

    return latest_date, latest_price, history_csv_path, png_path


def save_intraday_chart(run_ts, ticker="BZ=F", period="5d", interval="1h", ma_window=5):
    """Crea grafico intraday con istogrammi e moving average"""
    logging.info("=== INIZIO save_intraday_chart ===")
    
    intra = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if intra.empty:
        logging.error("No intraday data available")
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

    # CREAZIONE GRAFICO - CODICE ORIGINALE PERFETTO
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
    
    logging.info(f"Grafico intraday salvato: {png_path}")
    logging.info("=== FINE save_intraday_chart ===")

    return png_path


def send_email(subject, body, attachments):
    """Invia email con allegati via SMTP Gmail"""
    logging.info("=== INIZIO send_email ===")
    
    sender_email = os.environ["CRUDE_GMAIL_USER"]
    app_password = os.environ["CRUDE_GMAIL_APP_PASSWORD"]
    recipient_email = "accounting@perbellini.info"
    
    logging.info(f"Sender: {sender_email}")
    logging.info(f"Recipient: {recipient_email}")
    logging.info(f"Subject: {subject}")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    for file_path in attachments:
        logging.info(f"Allego file: {file_path}")
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{Path(file_path).name}"')
        msg.attach(part)
        logging.info(f"File allegato: {Path(file_path).name}")

    logging.info("Connessione a smtp.gmail.com:587...")
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            logging.info("Connessione SMTP stabilita")
            server.starttls(context=context)
            logging.info("TLS avviato")
            
            server.login(sender_email, app_password)
            logging.info("Login SMTP riuscito")
            
            server.sendmail(sender_email, recipient_email, msg.as_string())
            logging.info("Email inviata con successo!")
            
            server.quit()
            logging.info("Connessione SMTP chiusa")
            
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Errore autenticazione SMTP: {str(e)}")
        raise
    except smtplib.SMTPException as e:
        logging.error(f"Errore SMTP: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Errore invio email: {str(e)}")
        raise
    
    logging.info("=== FINE send_email ===")


def main():
    """Funzione principale"""
    logging.info("========================================")
    logging.info("INIZIO ESECUZIONE crude_daily.py")
    logging.info(f"Timestamp: {datetime.now().isoformat()}")
    logging.info("========================================")
    
    try:
        run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # ORA CORRENTE per l'oggetto della mail
        now = datetime.now()
        
        logging.info("Step 1: Generazione grafico daily...")
        latest_date, latest_price, history_csv, daily_png = save_daily_chart(run_ts)
        
        logging.info("Step 2: Generazione grafico intraday...")
        intra_png = save_intraday_chart(run_ts)
        
        logging.info("Step 3: Preparazione email...")
        
        # OGGETTO EMAIL con orario corrente (non latest_date)
        timestamp_subject = now.strftime("%Y-%m-%d %H:%M")
        subject = f"Brent Crude Oil Update - {timestamp_subject}"
        
        # BODY EMAIL formattato con emoji e bullet points
        body = f"""Ciao,

Ecco l'aggiornamento sul prezzo del Brent Crude Oil:

📊 Ultimo prezzo di chiusura: {latest_price:.2f} USD/barrel

In allegato trovi:
- Grafico daily (ultimi 20 giorni)
- Grafico intraday (oggi)
- Dati storici in formato CSV

Buona giornata!"""
        
        logging.info("Step 4: Invio email...")
        send_email(subject, body, [daily_png, intra_png, history_csv])
        
        logging.info("========================================")
        logging.info("ESECUZIONE COMPLETATA CON SUCCESSO")
        logging.info(f"Sent email with latest close {latest_price:.2f} USD/barrel")
        logging.info(f"Saved: {history_csv}")
        logging.info(f"Saved: {daily_png}")
        logging.info(f"Saved: {intra_png}")
        logging.info("========================================")
        
    except Exception as e:
        logging.error(f"ERRORE FATALE: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
