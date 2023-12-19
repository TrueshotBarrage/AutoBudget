# AutoBudget

AutoBudget: A simple tool to automatically record money transactions into a format of your choice.

## Setup

1. Install Python 3.7 or higher. I'm personally using Python 3.9.6.
2. Install the required packages using `pip install -r requirements.txt`
3. Create a OAuth2 client ID for the Gmail API and download the `credentials.json` file.
4. Move the `credentials.json` file to the root directory of the project.
5. Rename the `example_config.json` file to `config.json` and replace the `database_details` with your own Postgres DB instance.
6. Run `python gmail_client.py` to start the program.
