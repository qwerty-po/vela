import discord
from app.chat.models import VelaGPT


class Bot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.vela_gpts: dict[discord.TextChannel, VelaGPT] = {}

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.channel.name != "qwerty-디코봇-개발일지":
            return

        if self.user.mentioned_in(message):
            async with message.channel.typing():
                if message.channel not in self.vela_gpts:
                    self.vela_gpts[message.channel] = VelaGPT()
                response = await self.vela_gpts[message.channel].get_response(message)

                await message.reply(response)
