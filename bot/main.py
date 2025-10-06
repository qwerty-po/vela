from pathlib import Path

import discord
from app.bot import Bot
from config import Config

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(intents=intents)
    config = Config(Path(__file__).parent / "config.toml")

    bot.run(config.config_model.bot.token)
