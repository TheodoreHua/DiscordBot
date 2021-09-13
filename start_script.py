import sys
import logging
from os import system
from os.path import isfile

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")
crash_count = 1

def start_script():
    global crash_count

    if not isfile("maintain.txt"):
        with open("maintain.txt", "w") as f:
            f.write("y")
    while True:
        try:
            system("{} bot.py".format(sys.executable))
        except:
            logging.exception("Program exited x{:,}, restarting...".format(crash_count))
            crash_count += 1
        with open("maintain.txt") as f:
            if f.read() != "y":
                break
    with open("maintain.txt", "w") as f:
        f.write("y")


if __name__ == "__main__":
    start_script()
