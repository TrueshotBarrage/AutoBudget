from datetime import datetime
from flask import Flask

from gmail_client import main as abg_pipeline

app = Flask(__name__)


# A simple setup
@app.route("/")
def root():
    return "=== AutoBudget Pipeline Base ==="


@app.route("/run")
def run_gmail_client():
    logs = abg_pipeline()

    log_out = ""
    with open(f"log_{datetime.now().strftime('%m_%d_%Y_%H_%M')}.txt", "w") as f:
        for line in logs:
            f.write(f"{line}\n")
            log_out += f"{line}\n"

    return f"AutoBudget Pipeline Run Successful.\n\n{log_out}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="3000", debug=True)
