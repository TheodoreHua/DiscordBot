import json
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

class BotConfig:
    def __init__(self):
        with open("data/bot_config.json") as f:
            self.__config__ = json.load(f)
    
    def __getitem__(self, key):
        return self.__config__[key]

    def __len__(self):
        return len(self.__config__)

class ServerConfig:
    def __init__(self, bot_config):
        with open("data/server_config.json") as f:
            self.__config__ = json.load(f)
        self.bot_config = bot_config
        self.defaults = {"prefix": self.bot_config["prefix"], "auto_unarchive_threads": [], "aliases": {}}

    def __getitem__(self, key):
        return self.__config__[key]

    def __setitem__(self, key, item):
        self.__config__[key] = item

    def __len__(self):
        return len(self.__config__)

    def __delitem__(self, key):
        del self.__config__[key]

    def write_config(self):
        with open("data/server_config.json", "w") as f:
            json.dump(self.__config__, f, indent=2)

    def get_prefix(self, client, message):
        """Method to be passed to a commands.Bot instance in order to dynamically generate a prefix per server"""
        if message.guild is None:
            return self.defaults["prefix"]
        return self.__config__[str(message.guild.id)]["prefix"]

    def add_guild(self, guild):
        """Method to add a guild once invited"""
        self.__config__[str(guild.id)] = self.defaults
        logging.info("Added guild {} ({}) to guild config".format(guild.name, guild.id))

    def remove_guild(self, guild):
        """Method to remove a guild once kicked"""
        del self.__config__[str(guild.id)]
        logging.info("Added guild {} ({}) to guild config".format(guild.name, guild.id))

    def check_servers(self, guilds):
        """Method to check all servers the bot is present in is in the config"""
        w = False
        for guild in guilds:
            if str(guild.id) not in self.__config__.keys():
                logging.info("guild {} ({}) was not in guild config, created with defaults"
                             .format(guild.name, guild.id))
                self.__config__[str(guild.id)] = self.defaults
                w = True
            else:
                for key in self.defaults.keys():
                    if key not in self.__config__[str(guild.id)].keys():
                        logging.info("guild {} ({}) was missing key {} in config, created with default"
                                     .format(guild.name, guild.id, key))
                        self.__config__[str(guild.id)][key] = self.defaults[key]
                        w = True
        if w:
            logging.info("Overrode server config file after checking servers")
            self.write_config()

class UserConfig:
    def __init__(self):
        with open("data/user_config.json") as f:
            self.__config__ = json.load(f)
        self.defaults = {"reminders": {}}

    def __getitem__(self, key):
        return self.__config__[key]

    def __setitem__(self, key, item):
        self.__config__[key] = item

    def __delitem__(self, key):
        del self.__config__[key]

    def __len__(self):
        return len(self.__config__)

    def write_config(self):
        with open("data/user_config.json", "w") as f:
            json.dump(self.__config__, f, indent=2)

    def check_values(self):
        w = False
        for d in self.defaults:
            if d not in self.__config__:
                w = True
                self.__config__[d] = self.defaults[d]
        if w:
            logging.info("Overrode user config file after checking for missing keys")
            self.write_config()
