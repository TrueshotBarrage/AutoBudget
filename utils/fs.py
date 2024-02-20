import os
import json

env_vars = {
    "GOOGLE_CREDENTIALS": "credentials.json",
    "GOOGLE_TOKEN": "token.json",
    "APP_CONFIG": "config.json",
}


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

    for var in env_vars:
        if os.environ.get(var) and not os.path.isfile(env_vars[var]):
            os.system("echo ${" + var + "} > " + env_vars[var])

        assert os.path.isfile(env_vars[var])


def init_env_vars():
    env_var_dict = {}
    for var in env_vars:
        env_var_cfg = json.loads(
            os.environ.get(var) if var in os.environ else "null"
        )
        env_var_dict[var] = env_var_cfg

    return env_var_dict
