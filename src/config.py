from pydantic import BaseModel

from typing import Optional
import os

class Config(BaseModel):
    """ Application configuration.
    If this class gets updated be sure to updated the Setup > Configuration section in the README.md.

    Fields:
    - open_ai_api_key: API key for OpenAI
    - redis_host: Address on which Redis server is listening
    - redis_port: Port on which Redis server is listening
    - redis_db: Numeric identifier of database in Redis to access
    - discord_guild_id: ID of Discord server for which slash commands should be setup and handled
    - discord_bot_token: Discord API token
    - discord_channel_id: If provided the bot will only respond to messages in a channel with this ID, if not provided the bot will run in all channels
    """
    open_ai_api_key: str
    redis_host: str
    redis_port: int
    redis_db: int
    discord_guild_id: int
    discord_bot_token: set
    discord_channel_id: Optional[int]

    @staticmethod
    def from_env() -> "Config":
        """ Loads configuration from env vars.
        Env var names are the field names in all caps. Default values are as documented in README.md.

        Returns: Config object populated with env vars.
        """
        return Config({
            'open_ai_api_key': os.getenv('OPEN_AI_API_KEY'),
            'redis_host': os.getenv('REDIS_HOST', "redis"),
            'redis_port': os.getenv('REDIS_PORT', "6379"),
            'redis_db': os.getenv('REDIS_DB', "0"),
            'discord_guild_id': os.getenv('REDIS_GUILD_ID'),
            'discord_bot_token': os.getenv('REDIS_BOT_TOKEN'),
            'discord_channel_id': os.getenv('DISCORD_CHANNEL_ID'),
        })