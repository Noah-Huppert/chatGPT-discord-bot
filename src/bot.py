import discord
import redis.asyncio as redis

from src.openai_client import OpenAI, MAX_PROMPT_LENGTH
from src.message_history import ConversationHistoryRepo, UsernamesMapper, HistoryMessage

from typing import Optional, List, Dict, Protocol
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

class DiscordUsernameNotFound(Exception):
    """ Indicates the DiscordUsernamesMapper could not find a user's username.
    Fields:
    - user_id: ID of user who's username could not be found
    """
    user_id: int

    def __init__(self, user_id: int):
        super().__init__(f"Username of user with ID '{user_id}' could not be found")
        self.user_id = user_id

class NullUsernamesMapper(UsernamesMapper):
    async def get_username(self, user_id: int) -> str:
        return ""

class DiscordUsernamesMapper(UsernamesMapper):
    """ Implements UsernamesMapper using Discord.
    Fields:
    - discord_client: Discord client
    - cache: Records usernames which have already been retrieved, keys: user IDs, values: usernames
    """
    discord_client: discord.Client
    cache: Dict[int, str]

    def __init__(self, discord_client: discord.Client):
        """ Initializes.
        Arguments:
        - discord_client: Discord client
        """
        self.discord_client = discord_client
        self.cache = {}

    async def get_username(self, user_id: int) -> str:
        """ Get a user's Discord username.
        Raises:
        - DiscordUsernameNotFound: If user was not found

        Returns: Discord username
        """
        if user_id in self.cache:
            return self.cache[user_id]
        
        user = await self.discord_client.get_or_fetch_user(user_id)
        if user is None:
            raise DiscordUsernameNotFound(user_id)

        self.cache[user_id] = user.display_name

        return user.display_name

class DiscordInteractionHandler(Protocol):
    def __call__(self, interaction: discord.Interaction, *args, **kwargs) -> None: ...

class DiscordBot(discord.Bot):
    """ Discord bot client.
    Fields:
    - logger: Logger
    - guild_ids: Discord server IDs for which bot will respond
    - conversation_history_repo: Message history repository
    - openai_client: OpenAI API client
    """
    logger: logging.Logger
    guild_ids: List[int]
    conversation_history_repo: ConversationHistoryRepo
    openai_client: OpenAI

    def __init__(
        self,
        logger: logging.Logger,
        guild_ids: List[int],
        conversation_history_repo: ConversationHistoryRepo,
        openai_client: OpenAI
    ) -> None:
        super().__init__(intents=discord.Intents.default())
        self.logger = logger
        self.guild_ids = guild_ids

        self.conversation_history_repo = conversation_history_repo
        self.conversation_history_repo.usernames_mapper = DiscordUsernamesMapper(self)

        self.openai_client = openai_client

        self.slash_command(name="chat", description="Chat with GPT3", guild_ids=self.guild_ids)(self.chat)

    async def on_ready(self):
        self.logger.info("Ready")

    def compose_error_msg(self, msg: str) -> str:
        return f"> Error: {msg}"

    async def chat(self, interaction: discord.Interaction, prompt: str):
        """ /chat <prompt>
        User gives the bot a prompt and it responds with GPT3.
        Arguments:
        - interaction: Slash command interaction
        - prompt: Slash command prompt argument
        """
        try:
            self.logger.info("received /chat %s", prompt)
            await interaction.response.defer()

            # Check prompt isn't too long
            if len(prompt) > MAX_PROMPT_LENGTH:
                await interaction.followup.send(content=self.compose_error_msg(f"Prompt cannot me longer than {MAX_PROMPT_LENGTH} characters"))
                return

            # Record the user's prompt in their history
            history = await self.conversation_history_repo.get(interaction.user.id)
            async with await history.lock():
                # Record user's prompt and a blank message for the AI
                history.messages.extend([
                    HistoryMessage(
                        author_id=interaction.user.id,
                        body=prompt,
                    ),
                    HistoryMessage(
                        author_id=self.user.id,
                        body="",
                    ),
                ])
                await history.trim(MAX_PROMPT_LENGTH)

                # Ask AI
                transcript = "\n".join((await history.as_transcript_lines())[0])
                ai_resp = await self.openai_client.create_completion(transcript)
                if ai_resp is None:
                    self.logger("No AI response")
                    await interaction.followup.send(self.compose_error_msg("The AI did not know what to say"))
                    return

                history.messages[-1].body = ai_resp
                await history.trim(MAX_PROMPT_LENGTH)

                await history.save()

                resp_txt = "> {prompt}\n{ai_resp}".format(prompt=prompt, ai_resp=ai_resp)
                await interaction.followup.send(content=resp_txt)
        except Exception as e:
            self.logger.exception("Failed to run /chat handler: %s", e)

            try:
                await interaction.followup.send(content=self.compose_error_msg("An unexpected error occurred"))
            except Exception as e:
                self.logger.exception("While trying to send an 'unknown error' message to the user, an exception occurred: %s", e)

async def run_bot():
    logger.info("Run bot started")

    logger.info("Connecting to Redis")

    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', "redis"),
        port=int(os.getenv('REDIS_PORT', "6379")),
        db=int(os.getenv('REDIS_DB', "0")),
    )

    await redis_client.ping()

    logger.info("Connected to Redis")

    bot = DiscordBot(
        logger=logger.getChild("discord.bot"),
        guild_ids=[int(os.getenv('DISCORD_GUILD_ID'))],
        conversation_history_repo=ConversationHistoryRepo(
            redis_client=redis_client,
            usernames_mapper=NullUsernamesMapper(),
        ),
        openai_client=OpenAI(),
    )

    logger.info("Starting bot")
    
    await bot.start(os.getenv('DISCORD_BOT_TOKEN'))