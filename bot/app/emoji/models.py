from hashlib import sha256

import discord
import requests


class EmojiStealModel:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.emoji_image_hashes: set[str] = set(
            sha256(self._fetch_emoji_image(emoji.url)).hexdigest()
            for emoji in guild.emojis
        )

    async def steal_emojies_from_forwarded_message(
        self, message: discord.Message
    ) -> list[discord.Emoji]:
        emojies_name: set[str] = set()

        for word in message.message_snapshots[0].content.split():
            if word.startswith("<:") and word.endswith(">"):
                emojies_name.add(word[2:-1])

        result: list[discord.Emoji] = []
        for emoji_name in emojies_name:
            cdn = discord.PartialEmoji.from_str(emoji_name).url
            if cdn is None:
                continue

            emoji_image = self._fetch_emoji_image(cdn)
            if not emoji_image:
                continue

            if self._check_already_same_emoji_exists(emoji_image):
                continue

            try:
                emoji_name = emoji_name.split(":")[0]
                new_emoji = await self.guild.create_custom_emoji(
                    name=emoji_name, image=emoji_image
                )
                result.append(new_emoji)
            except discord.HTTPException:
                continue
        return result

    def _fetch_emoji_image(self, url: str) -> bytes:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            return b""

    def _check_already_same_emoji_exists(self, new_emoji: bytes) -> bool:
        new_emoji_hash = sha256(new_emoji).hexdigest()
        if new_emoji_hash in self.emoji_image_hashes:
            return True
        self.emoji_image_hashes.add(new_emoji_hash)
        return False
