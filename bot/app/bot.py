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
            await self._steal_emoji_from_message(message)

    async def _steal_emoji_from_message(self, message: discord.Message):
        async with message.channel.typing():
            emoji_stealer = EmojiStealModel(guild=message.guild)
            emojies = await emoji_stealer.steal_emojies_from_forwarded_message(message)

            await message.add_reaction("<:vela_curious:1424979897520230410>")
            if emojies:
                await message.reply(
                    f"새로운 이모지들이네? 여기에도 추가해야겠어! {''.join(self._contextable_string_from_emoji(emoji) for emoji in emojies)}"
                )
            else:
                await message.reply("이미 있는 이모지들이야?")

    @staticmethod
    def _contextable_string_from_emoji(emoji: discord.Emoji) -> str:
        return f"<:{emoji.name}:{emoji.id}>"
