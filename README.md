# AutoBudget

AutoBudget is a Python-based automation tool that scrapes transaction emails from Gmail, parses them for financial data (date, amount, vendor), and stores them in a PostgreSQL database. It also includes utilities for exporting this data to CSV, which can be synced to cloud storage (e.g., Google Drive) for further analysis.

## Features

- **Gmail Integration**: Securely connects to Gmail using OAuth2.
- **Smart Parsing**: Configurable regex and string matching patterns to extract transaction details from various bank/service emails (Venmo, Amex, Chase, etc.).
- **Database Storage**: Stores transactions in a PostgreSQL database with deduplication.
- **Web Interface**: Simple Flask server to trigger the pipeline via HTTP.
- **Export Automation**: Script to export database records to CSV, suitable for cron automation.

## Prerequisites

- **Python 3.8+**
- **PostgreSQL Database**: You need a running Postgres instance (local or cloud, e.g., Supabase, AWS RDS).
- **Google Cloud Project**: A project with the **Gmail API** enabled.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/autobudget.git
    cd autobudget
    ```

2.  **Set up a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

### 1. Google Credentials

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project and enable the **Gmail API**.
3.  Configure the OAuth consent screen (add your email as a test user).
4.  Create **OAuth 2.0 Client IDs** (Desktop App).
5.  Download the JSON file, rename it to `credentials.json`, and place it in the project root.

_Note: On the first run, a browser window will open to authorize access. A `token.json` file will be generated for subsequent non-interactive runs._

### 2. Application Config (`config.json`)

Copy the example config to create your production config:

```bash
cp example_config.json config.json
```

Edit `config.json` to match your setup:

- **database_details**: Enter your PostgreSQL connection info.
- **clients**: Define the email folders and parsing logic for each bank/card.
  - `folder`: The Gmail label/folder name where these emails are stored.
  - `match_pattern`: Logic to extract data.
    - `use_regex`: `true` or `false`.
    - `amount`, `date`, `vendor`: Regex groups or string delimiters.

### 3. Database Initialization

The application automatically initializes the database schema using `db_init.sql` when it connects. Ensure your database user has permissions to create tables.

## Usage

### Running the Pipeline Manually

To fetch emails, parse them, and save to the database:

```bash
python gmail_client.py
```

### Running the Web Server

To start the Flask server (defaults to port 3000):

```bash
python server.py
```

Trigger the pipeline by visiting: `http://localhost:3000/run`

### Exporting Data

To export the `messages` table to a CSV file:

1.  Edit `export_transactions.py` to set your desired `EXPORT_PATH`.
2.  Run the script:
    ```bash
    python export_transactions.py
    ```

## Automation (Cron Setup)

You can automate the data export (e.g., to sync with Google Drive) using a cron job.

1.  **Make the export script executable:**

    ```bash
    chmod +x export_transactions.py
    ```

2.  **Edit your crontab:**

    ```bash
    crontab -e
    ```

3.  **Add the cron entry:**
    Example: Run daily at 9:00 AM.
    _Replace `/path/to/autobudget` with your actual project path._

    This will:

    - Run `gmail_client.py` to fetch and load new transactions into the database.
    - Then run `export_transactions.py` to export the updated `messages` table to CSV.

    ```cron
    0 9 * * * cd /path/to/autobudget && /path/to/autobudget/venv/bin/python3 gmail_client.py >> /tmp/autobudget_gmail.log 2>&1 && /path/to/autobudget/venv/bin/python3 export_transactions.py >> /tmp/autobudget_export.log 2>&1
    ```

## Project Structure

- `gmail_client.py`: Core logic for fetching and parsing emails.
- `server.py`: Flask web server.
- `export_transactions.py`: Script for CSV export.
- `utils/`: Helper modules for database, config, parsing, and logging.
- `db_init.sql`: Database schema definition.
- `config.json`: User configuration (ignored by git).
