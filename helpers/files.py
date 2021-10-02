import json
import logging
from os import mkdir
from os.path import isfile, isdir

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

default_bot_config = {
    "owner_id": None,
    "description": "A bot with various random utilities, some useful, some not",
    "status": "!help",
    "prefix": "!",
    "embed_colour": 7857407,
    "snekbox": "",
    "hastebin": "https://hastebin.com/",
    "ud_rapidapi_key": ""
}

def assert_data():
    # Basic checks to see if the directory and files exist
    if not isdir("data"):
        mkdir("data")
    if not isfile("data/bot_config.json"):
        with open("data/bot_config.json", "w") as f:
            logging.fatal("Bot config did not exist and has been generated, please fill it in")
            json.dump(default_bot_config, f, indent=2)
            exit()
    if not isfile("data/server_config.json"):
        with open("data/server_config.json", "w") as f:
            logging.info("Created server config file")
            json.dump({}, f, indent=2)
    if not isfile("data/user_config.json"):
        with open("data/user_config.json", "w") as f:
            logging.info("Created user config file")
            json.dump({}, f, indent=2)

    # More advanced checks to see if bot config is missing required keys
    with open("data/bot_config.json", "r") as f:
        data = json.load(f)
        missing_keys = []
        for key in default_bot_config.keys():
            if key not in data.keys():
                missing_keys.append(key)

    if len(missing_keys) > 0:
        logging.error("Missing {} keys ({}), they have been pre-filled with default values. You may want to change them"
                      " before starting the bot again".format(
            len(missing_keys), ", ".join(missing_keys)))
        with open("data/bot_config.json", "w") as f:
            for key in missing_keys:
                data[key] = default_bot_config[key]
            json.dump(data, f, indent=2)
        exit()
