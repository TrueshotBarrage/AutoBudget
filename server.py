from datetime import datetime
import logging

from flask import Flask

from gmail_client import main as abg_pipeline
import utils.fs as fs

logging.basicConfig(
    level=logging.INFO, format="%(levelname)-9s %(asctime)s - [%(name)s] %(message)s"
)
logger = logging.getLogger("AutoBudget Server")

app = Flask(__name__)


# A simple setup
@app.route("/")
def root():
    return "=== AutoBudget Pipeline Base ==="


@app.route("/run")
def run_gmail_client():
    # fs._initialize_env_vars_into_files()
    logger.info("Initializing env vars...")
    env_vars = fs.init_env_vars()

    logger.info("Executing AutoBudget pipeline...")
    logs = abg_pipeline(env_vars)
    logger.info("AutoBudget pipeline successfully executed. Now logging the output artifacts...")

    log_out = ""
    with open(f"log_{datetime.now().strftime('%m_%d_%Y_%H_%M')}.txt", "w") as f:
        for line in logs:
            f.write(f"{line}\n")
            log_out += f"{line}\n"

    success_msg = f"AutoBudget Pipeline Run Successful.\n\n{log_out}"
    logger.info(success_msg)

    return success_msg


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="3000", debug=True)
