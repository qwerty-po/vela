import discord
from app.chat.models import VelaGPT
from app.emoji.models import EmojiStealModel


class Bot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.vela_gpts: dict[discord.TextChannel, VelaGPT] = {}

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.channel.name != "qwerty-디코봇-개발일지":
            return

        if message.type == discord.MessageType.default and message.flags.forwarded:
            async with message.channel.typing():
                emoji_stealer = EmojiStealModel(guild=message.guild)
                emojies = await emoji_stealer.steal_emojies_from_forwarded_message(
                    message
                )

                for emoji in emojies:
                    await message.channel.send(f"이모지 {emoji} 추가했어!")
