# Chat GPT Discord Bot
Provides access to OpenAI models via a Discord bot.

# Table Of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Development](#development)
- [Release Instructions](#release-instructions)

# Overview
A Python Discord bot which provides access to OpenAI's GPT3. Inspired by [@Zero6992's chatGPT-discord-bot repository](https://github.com/Zero6992/chatGPT-discord-bot). Provides the modifications:

- Major components rewritten
   - Using PyCord instead of DiscordPy
   - Env vars used for configuration
   - Python virtual environment
   - Docker development setup
- Features added
   - History between bot and users saved in Redis
   - Provides a transcript of the bot's conversation as part of the GPT3 prompt so the model appears to "remember" a portion of the conversation

# Setup
## Configuration
Configuration values are set via the following environment variables:
- `OPENAI_API_KEY`: Your OpenAPI API key
- Redis
   - `REDIS_HOST`: Hostname of Redis server (Default: `redis`)
   - `REDIS_PORT`: Port number of Redis server (Default: `6379`)
   - `REDIS_DB`: Database number of Redis server (Default: `0`)
- Discord
   - `DISCORD_GUILD_ID`: ID of Discord server in which Bot will run
   - `DISCORD_BOT_TOKEN`: API token for Discord bot
   - `DISCORD_CHANNEL_ID`: If provided then the bot will only interact in the provided channel

## Install & Run
Pipenv is used to manage a Python virtual environment. Install dependencies and then activate the environment:

```
pipenv install
pipenv shell
```

Then run the bot:

```
python ./main.py
```

The [`Dockerfile`](./Dockerfile) in the repository root performs these steps automatically. The [`docker-compose-prod.yaml`](./docker-compose-prod.yaml) file runs this Docker image.

# Development
The [`docker-compose.yaml`](./docker-compose.yaml) and [`dev.Dockerfile`](./dev.Dockerfile) files provide a development environment which is pre-setup. To use:

1. Make a copy of `dev-example.env` named `dev.env` and fill in your own values
2. Launch the Docker Compose stack:
   ```
   docker compose up -d --build
   ```

To run type checking open a shell in the `chatgpt-discord-bot` container and run `pyright`.

# Release Instructions
1. Build the Docker image:
   ```
   docker build -t noahhuppert/chatgpt-discord-bot:vx.y.z
   ```
2. Push the Docker image
   ```
   docker push noahhuppert/chatgpt-discord-bot:vx.y.z
   ```
3. Create a new [GitHub Release](https://github.com/Noah-Huppert/chatGPT-discord-bot/releases)
   - Include a short description of the changes
   - Include the Docker image tag by writing:
     ```
     Docker image: `noahhuppert/chatgpt-discord-bot:vx.y.z`
     ```