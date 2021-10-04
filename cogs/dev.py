import re
import requests
import textwrap
from time import time
from signal import Signals

from nextcord.ext import commands

ESCAPE_REGEX = re.compile("[`\u202E\u200B]{3,}")
FORMATTED_CODE_REGEX = re.compile(
    r"(?P<delim>(?P<block>```)|``?)"        # code delimiter: 1-3 backticks; (?P=block) only matches if it's a block
    r"(?(block)(?:(?P<lang>[a-z]+)\n)?)"    # if we're in a block, match optional language (only letters plus newline)
    r"(?:[ \t]*\n)*"                        # any blank (empty or tabs/spaces only) lines before the code
    r"(?P<code>.*?)"                        # extract all code inside the markup
    r"\s*"                                  # any more whitespace before the end of the code markup
    r"(?P=delim)",                          # match the exact same delimiter from the start again
    re.DOTALL | re.IGNORECASE               # "." also matches newlines, case insensitive
)
RAW_CODE_REGEX = re.compile(
    r"^(?:[ \t]*\n)*"                       # any blank (empty or tabs/spaces only) lines before the code
    r"(?P<code>.*?)"                        # extract all the rest as code
    r"\s*$",                                # any trailing whitespace until the end of the string
    re.DOTALL                               # "." also matches newlines
)

class Dev(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config
        self.jobs = {}

    @staticmethod
    def get_results_message(results: dict):
        """Return a user-friendly message and error corresponding to the process's return code."""
        stdout, returncode = results["stdout"], results["returncode"]
        msg = f"Your eval job has completed with return code {returncode}"
        error = ""

        if returncode is None:
            msg = "Your eval job has failed"
            error = stdout.strip()
        elif returncode == 137:
            msg = "Your eval job timed out or ran out of memory"
        elif returncode == 255:
            msg = "Your eval job has failed"
            error = "A fatal NsJail error occurred"
        else:
            # Try to append signal's name if one exists
            try:
                name = Signals(returncode - 128).name
                msg = f"{msg} ({name})"
            except ValueError:
                pass

        return msg, error

    @staticmethod
    def prepare_input(code):
        if match := list(FORMATTED_CODE_REGEX.finditer(code)):
            blocks = [block for block in match if block.group("block")]

            if len(blocks) > 1:
                code = '\n'.join(block.group("code") for block in blocks)
            else:
                match = match[0] if len(blocks) == 0 else blocks[0]
                code, block, lang, delim = match.group("code", "block", "lang", "delim")
        else:
            code = RAW_CODE_REGEX.fullmatch(code).group("code")

        code = textwrap.dedent(code)
        return code

    async def format_output(self, output: str):
        """
        Format the output and return a tuple of the formatted output and a URL to the full output.
        Prepend each line with a line number. Truncate if there are over 10 lines or 1000 characters
        and upload the full output to a paste service.
        """
        output = output.rstrip("\n")
        original_output = output  # To be uploaded to a pasting service if needed
        paste_link = None

        if "<@" in output:
            output = output.replace("<@", "<@\u200B")  # Zero-width space

        if "<!@" in output:
            output = output.replace("<!@", "<!@\u200B")  # Zero-width space

        if ESCAPE_REGEX.findall(output):
            r = requests.post(self.bot_config["hastebin"] + "documents", data=original_output.encode("utf-8"))
            paste_link = self.bot_config["hastebin"] + r.json()["key"] if r.ok else None
            return "Code block escape attempt detected; will not output result", paste_link

        truncated = False
        lines = output.count("\n")

        if lines > 0:
            output = [f"{i:03d} | {line}" for i, line in enumerate(output.split('\n'), 1)]
            output = output[:11]
            output = "\n".join(output)

        if lines > 10:
            truncated = True
            if len(output) >= 1000:
                output = f"{output[:1000]}\n... (truncated - too long, too many lines)"
            else:
                output = f"{output}\n... (truncated - too many lines)"
        elif len(output) >= 1000:
            truncated = True
            output = f"{output[:1000]}\n... (truncated - too long)"

        if truncated:
            r = requests.post(self.bot_config["hastebin"] + "documents", data=original_output.encode("utf-8"))
            paste_link = self.bot_config["hastebin"] + r.json()["key"] if r.ok else None

        output = output or "[No Output]"

        return output, paste_link

    async def send_eval(self, ctx, code):
        async with ctx.typing():
            r = requests.post(self.bot_config["snekbox"], json={"input": code})
            if not r.ok:
                print(repr(r), r.ok, r.text)
                return None
            else:
                results = r.json()
            msg, error = self.get_results_message(r.json())

            if error:
                output, paste_link = error, None
            else:
                output, paste_link = await self.format_output(results["stdout"])

            if not results["stdout"].strip():  # No output
                icon = ":warning:"
            elif results["returncode"] == 0:  # No error
                icon = ":white_check_mark:"
            else:  # Exception
                icon = ":x:"
            msg = f"{ctx.author.mention} {icon} {msg}.\n\n```\n{output}\n```"
            if paste_link:
                msg = f"{msg}\nFull output: {paste_link}"

            response = await ctx.send(msg)
        return response

    @commands.command(name="eval", aliases=["e"], brief="Run some Python code and get the results",
                      usage="<code>")
    async def _eval(self, ctx, *, code=None):
        """Run your Python code and get the output of it, code will timeout after around 6 seconds, and you can run this
        command one at a time (you have to wait for one to finish before you run another)."""
        if ctx.author.id in self.jobs:
            return await ctx.send("You already have an eval job running, please wait for it to finish")
        if not code:
            return await ctx.send_help(ctx.command)

        self.jobs[ctx.author.id] = time()
        code = self.prepare_input(code)
        try:
            resp = await self.send_eval(ctx, code)
        finally:
            del self.jobs[ctx.author.id]

        if resp is None:
            return await ctx.send("Error running code in snekbox, try again later")
