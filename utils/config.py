import json
from typing import Dict, List, Union


class Config:
    """
    A class that represents the config file.
    """

    def __init__(self, config_path="config.json", config_dict=None):
        self.config_path = config_path
        self.config_dict = config_dict
        self.items = config_dict if config_dict else self.load(self.config_path)
        self.ConfigType = Dict[
            str,
            Union[
                Dict[str, str],
                List[Dict[str, Union[str, Dict[str, Union[List[str], str]]]]],
            ],
        ]

    def __repr__(self):
        return f"Config({self.config_path})"

    def __str__(self):
        return f"Config file path: {self.config_path}"

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    def __delitem__(self, key):
        del self.items[key]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __type__(self):
        return self.ConfigType

    def save(self):
        """
        Saves the config file.
        """
        with open(self.config_path, "w") as config_file:
            json.dump(self.items, config_file, indent=2)

    def load(self, config_path="config.json"):
        """
        Opens the config file and returns the contents as a dictionary.
        Args:
            config_path (str): The file path of the config JSON.
        Returns:
            dict: The config dict.
        """
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        return config

    def print(self, contents=None):
        """
        Pretty prints the config file.
        Args:
            contents (dict): The contents to pretty print.
        """
        if contents is None:
            print(json.dumps(self.items, indent=2))
        else:
            print(json.dumps(contents, indent=2))

    def get_email_clients(self, type=None) -> List[Dict[str, str]]:
        """
        Returns a list of email clients from the config file.
        Args:
            type (str): Only return clients of this type.
        Returns:
            List[Dict[str, str]]: A list of email clients.
        """
        if type is None:
            return self.items["clients"]
        return [
            client for client in self.items["clients"] if client["type"] == type
        ]

    def get_folders(self, type=None) -> List[str]:
        """
        Returns a list of folders to extract emails from the config file.
        Flatten the list of folders.
        Args:
            type (str): Only return folders of clients of this type.
        Returns:
            List[str]: A list of folders.
        """
        if type is None:
            return [client["folder"] for client in self.items["clients"]]
        return [
            client["folder"]
            for client in self.items["clients"]
            if client["type"] == type
        ]

    def get_match_pattern(
        self, folder_name
    ) -> Dict[str, Union[List[str], str]]:
        """
        Returns the match patterns for each attribute needed from the email for
        a given folder.
        Args:
            folder_name (str): Used to find the desired match pattern.
        Returns:
            Dict[str, Union[List[str], str]]: The match pattern dict with keys
            "use_regex", "regex", "amount", "date", and "vendor".
        Raises:
            IndexError: Raised if the input folder name does not exist.
        """
        for client in self.items["clients"]:
            if client["folder"] == folder_name:
                return client["match_pattern"]

        raise IndexError(f"Folder name '{folder_name}' was not found in config")

    def get_db_details(self) -> Dict[str, str]:
        """
        Get the database connection details.
        Returns:
            Dict[str, str]: The database configuration items.
        """
        return self.items["database_details"]
