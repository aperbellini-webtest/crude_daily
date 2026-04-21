import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import ssl
import os
import sys
from email.message import EmailMessage
from datetime import datetime
import logging

# Configurazione logging dettagliato
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/crude_debug.log')
    ]
)

def save_daily_chart():
    """Scarica dati daily e crea grafico"""
    logging.info("=== INIZIO save_daily_chart ===")
    
    # Scarica dati Brent Crude Oil
    logging.info("Download dati da Yahoo Finance...")
    ticker = yf.Ticker("BZ=F")
    
    # Ultimi 20 giorni di trading
    hist = ticker.history(period="1mo")
    hist = hist.tail(20)
    
    # Salva CSV
    csv_file = "crude_daily_history.csv"
    hist.to_csv(csv_file)
    logging.info(f"CSV salvato: {csv_file}")
    
    # Crea grafico
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(hist.index, hist['Close'], linewidth=2, color='blue', label='Close Price')
    ax.set_title('Brent Crude Oil - Daily Close Price (Last 20 days)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price (USD/barrel)', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Salva PNG con timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    daily_png = f"crude_daily_daily_{timestamp}.png"
    plt.savefig(daily_png, dpi=300)
    plt.close()
    logging.info(f"Grafico daily salvato: {daily_png}")
    
    return hist, csv_file, daily_png


def save_intraday_chart():
    """Crea grafico intraday con ultime quotazioni"""
    logging.info("=== INIZIO save_intraday_chart ===")
    
    # Scarica dati intraday (1 giorno, intervallo 1h)
    ticker = yf.Ticker("BZ=F")
    hist = ticker.history(period="1d", interval="1h")
    
    if hist.empty:
        logging.warning("Nessun dato intraday disponibile")
        # Crea grafico vuoto con messaggio
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No intraday data available', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    else:
        logging.info(f"Dati intraday scaricati: {len(hist)} righe")
        # Crea grafico
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(hist.index, hist['Close'], linewidth=2, color='red', label='Intraday Price')
        ax.set_title('Brent Crude Oil - Intraday Price (Today)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price (USD/barrel)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
    
    # Salva PNG con timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    intra_png = f"crude_daily_intraday_{timestamp}.png"
    plt.savefig(intra_png, dpi=300)
    plt.close()
    logging.info(f"Grafico intraday salvato: {intra_png}")
    
    return intra_png


def send_email(subject, body, attachments):
    """Invia email con allegati via SMTP Gmail"""
    logging.info("=== INIZIO send_email ===")
    
    # Recupera credenziali dalle variabili d'ambiente
    sender_email = os.environ.get('CRUDE_GMAIL_USER')
    app_password = os.environ.get('CRUDE_GMAIL_APP_PASSWORD')
    recipient_email = "aperbellini@gmail.com"
    
    # Debug: verifica che le secrets esistano
    logging.info(f"Sender email configurata: {sender_email[:3] if sender_email else 'NONE'}***")
    logging.info(f"Password length: {len(app_password) if app_password else 0} caratteri")
    logging.info(f"Recipient: {recipient_email}")
    
    if not sender_email or not app_password:
        logging.error("ERRORE CRITICO: CRUDE_GMAIL_USER o CRUDE_GMAIL_APP_PASSWORD non sono impostate!")
        raise ValueError("Mancano le credenziali email nelle environment variables")
    
    # Crea messaggio email
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg.set_content(body)
    
    # Aggiungi allegati
    for attachment in attachments:
        try:
            logging.info(f"Allego file: {attachment}")
            with open(attachment, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(attachment)
            
            # Determina il tipo di file
            if attachment.endswith('.png'):
                msg.add_attachment(file_data, maintype='image', subtype='png', filename=file_name)
            elif attachment.endswith('.csv'):
                msg.add_attachment(file_data, maintype='text', subtype='csv', filename=file_name)
            else:
                msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)
            
            logging.info(f"File {file_name} allegato con successo")
        except Exception as e:
            logging.error(f"Errore nell'allegare {attachment}: {str(e)}")
            raise
    
    # Invia email via SMTP
    logging.info("Connessione a smtp.gmail.com:587...")
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            logging.info("Connessione SMTP stabilita")
            server.starttls(context=context)
            logging.info("TLS avviato")
            
            server.login(sender_email, app_password)
            logging.info("Login SMTP riuscito")
            
            # Invia email
            server.sendmail(sender_email, recipient_email, msg.as_string())
            logging.info("Email inviata con successo!")
            
            server.quit()
            logging.info("Connessione SMTP chiusa")
            
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Errore di autenticazione SMTP: {str(e)}")
        logging.error("Verifica che CRUDE_GMAIL_APP_PASSWORD sia corretta (deve essere una App Password, non la password normale)")
        raise
    except smtplib.SMTPException as e:
        logging.error(f"Errore SMTP durante l'invio: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Errore generico durante l'invio email: {str(e)}")
        raise
    
    logging.info("=== FINE send_email ===")


def main():
    """Funzione principale"""
    logging.info("========================================")
    logging.info("INIZIO ESECUZIONE crude_daily.py")
    logging.info(f"Timestamp: {datetime.now().isoformat()}")
    logging.info("========================================")
    
    try:
        # 1. Scarica dati e crea grafico daily
        logging.info("Step 1: Generazione grafico daily...")
        hist, history_csv, daily_png = save_daily_chart()
        latest_price = hist['Close'].iloc[-1]
        logging.info(f"Ultimo prezzo closing: {latest_price:.2f} USD/barrel")
        
        # 2. Crea grafico intraday
        logging.info("Step 2: Generazione grafico intraday...")
        intra_png = save_intraday_chart()
        
        # 3. Prepara email
        logging.info("Step 3: Preparazione email...")
        subject = f"Brent Crude Oil Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        body = f"""
Ciao,

Ecco l'aggiornamento sul prezzo del Brent Crude Oil:

📊 Ultimo prezzo di chiusura: {latest_price:.2f} USD/barrel

In allegato trovi:
- Grafico daily (ultimi 20 giorni)
- Grafico intraday (oggi)
- Dati storici in formato CSV

Buona giornata!
        """
        
        # 4. Invia email
        logging.info("Step 4: Invio email...")
        attachments = [history_csv, daily_png, intra_png]
        send_email(subject, body, attachments)
        
        logging.info("========================================")
        logging.info("ESECUZIONE COMPLETATA CON SUCCESSO")
        logging.info("========================================")
        
    except Exception as e:
        logging.error(f"ERRORE FATALE durante l'esecuzione: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
