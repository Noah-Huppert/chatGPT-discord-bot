import os
import json
from typing import List, Optional
import abc
import logging

from pydantic import BaseModel
import redis.asyncio as redis

class UsernamesMapper(abc.ABC):
    """ Converts user IDs to usernames.
    """

    @abc.abstractmethod
    async def get_username(self, user_id: int) -> str:
        """ Get a user's name.
        Arguments:
        - user_id: ID of user

        Raises: Any error if fails to get username

        Returns: Username
        """
        raise NotImplementedError()

class HistoryMessage(BaseModel):
    """ One message sent by one user.
    Fields:
    - author_id: ID of user who sent message
    - body: The text sent in the message
    """
    author_id: int
    body: str

    async def as_transcript_str(self, usernames_mapper: UsernamesMapper) -> str:
        """ Convert history message into a script format string.
        Arguments:
        - usernames_mapper: Implementation of username mapper
        Returns: History message in format <username>: <body>
        """
        return f"{await usernames_mapper.get_username(self.author_id)}: {self.body}"
    
class ConversationHistory(BaseModel):
    """ History of messages between users.
    Fields:
    - interacting_user_id: ID of the user (not the bot) with which the conversation is being had
    - messages: List of messages, ordered where first message is the oldest and last message is the newest
    """
    interacting_user_id: int
    messages: List[HistoryMessage]

    async def as_transcript_lines(self, usernames_mapper: UsernamesMapper) -> List[str]:
        """ Converts history into transcript lines.
        Arguments:
        - usernames_mapper: Implementation of username mapper

        Returns: List of transcript lines
        """
        lines = []
        for msg in self.messages:
            lines.append(await msg.as_transcript_str(usernames_mapper))

        return lines

    async def all_messages_transcript_len(self, usernames_mapper: UsernamesMapper) -> int:
        """ Count the length of all transcript lines.
        Arguments:
        - usernames_mapper: Implementation of username mapper

        Returns: Count in characters.
        """
        count = 0
        for line in await self.as_transcript_lines(usernames_mapper):
            count += len(line)

        return count

class MessageHistoryRepo:
    """ Records, retrieves, and manipulates message history.
    Message history is stored for conversations between the bot and a user. The history between the bot and multiple users is not stored because there is a maximum length which a prompt can be for GPT3, so the most relevant data (aka data between a specific user and the bot) is stored.
    
    Fields:
    - redis_client: The Redis client
    - username_mapper: Implementation of usernames mapper
    - redis_host: Redis server host
    - redis_port: Redis server port
    - redis_db: Redis server database number
    """
    redis_client: redis.Redis
    usernames_mapper: UsernamesMapper

    async def init(self, usernames_mapper: UsernamesMapper, redis_host: str, redis_port: int, redis_db: int):
        """ Initializes.
        Arguments:
        - host: Redis host
        - port: Redis port
        - db: Redis database number
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
        )
        self.usernames_mapper = usernames_mapper

        await self.redis_client.ping()

    def get_conversation_history_key(self, interacting_user_id: int) -> str:
        """ Generate the Redis key for a conversation history item.
        Arguments:
        - interacting_user_id: ID of user (not bot) with which the conversation is being had

        Returns: The redis key
        """
        return f"conversation-history:interacting-user-id:{interacting_user_id}"

    def get_conversation_history_lock_key(self, interacting_user_id: int) -> str:
        """ Generate the Redis key for a conversation history item's lock.
        Arguments:
        - interacting_user_id: ID of user (not bot) with which the conversation is being had

        Returns: The redis lock key
        """
        return f"conversation-history:interacting-user-id:{interacting_user_id}:lock"

    async def get_conversation_history(self, interacting_user_id: int) -> Optional[ConversationHistory]:
        """ Retrieve history for a conversation.
        Arguments:
        - interacting_user_id: ID of user (not bot) with which the conversation is being had

        Returns: The conversation history item, or None if not stored for the interacting_user_id
        """
        redis_key = self.get_conversation_history_key(interacting_user_id)

        # Retrieve data from Redis
        raw_json = await self.redis_client.get(redis_key)
        if raw_json is None:
            # Redis key does not exist
            return None
        
        parsed_json = json.loads(raw_json)

        return ConversationHistory(**parsed_json)

    async def save_conversation_history(self, history: ConversationHistory):
        """ Save conversation history.
        Arguments:
        - history: The conversation history to save
        """
        redis_key = self.get_conversation_history_key(history.interacting_user_id)
        raw_json = json.dumps(history.dict())

        await self.redis_client.set(redis_key, raw_json)

    async def append_message(self, interacting_user_id: int, msg: HistoryMessage, max_conversation_characters: int) -> ConversationHistory:
        """ Store a new message as part of a conversation.
        Ensures that with the new message the total size of all messages in the history does not exceed max_conversation_characters. If adding the message would exceed this limit then the oldest messages will be removed to make the new message fit.
        Arguments:
        - interacting_user_id: ID of the user (not the bot) with which this conversation is being had
        - msg: The message to store, should be the most recent message in the conversation
        - max_conversation_characters: The maximum number of characters which the total of all conversation items should not exceed

        Returns: The conversation history with the message added
        """
        # Acquire a lock so no one else modifies this history
        logging.info("getting lock")
        async with self.redis_client.lock(self.get_conversation_history_lock_key(interacting_user_id)):
            logging.info("locked")
            # Get existing history
            history = await self.get_conversation_history(interacting_user_id)

            if history is None:
                # Initialize new history
                history = ConversationHistory(
                    interacting_user_id=interacting_user_id,
                    messages=[],
                )

            # Append message
            history.messages.append(msg)

            # Remove messages until below max length
            history_len = await history.all_messages_transcript_len(self.usernames_mapper)

            while history_len > max_conversation_characters:
                # Remove oldest messages
                removed_msg = history.messages.pop(0)
                history_len -= len(removed_msg.as_transcript_str(self.usernames_mapper))

            logging.info("past trim")

            # Save new history
            await self.save_conversation_history(history)

            logging.info("saved")

            return history
