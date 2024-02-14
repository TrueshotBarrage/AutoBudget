import os


def _initialize_env_vars_into_files():
    if os.environ.get("GOOGLE_CREDENTIALS") and not os.path.isfile(
        "credentials.json"
    ):
        os.system("echo ${GOOGLE_CREDENTIALS} > credentials.json")

    if os.environ.get("GOOGLE_TOKEN") and not os.path.isfile("token.json"):
        os.system("echo ${GOOGLE_TOKEN} > token.json")

    if os.environ.get("APP_CONFIG") and not os.path.isfile("config.json"):
        os.system("echo ${APP_CONFIG} > config.json")

    assert os.path.isfile("credentials.json")
    assert os.path.isfile("token.json")
    assert os.path.isfile("config.json")
