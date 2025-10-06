import discord
from app.bot import Bot

if __name__ == "__main__":
    intents = discord.Intents.default()
    bot = Bot(intents=intents)
    bot.run("YOUR_TOKEN")
