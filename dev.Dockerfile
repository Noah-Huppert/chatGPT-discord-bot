FROM python:3.10

RUN mkdir -p /DiscordBot
WORKDIR /DiscordBot

COPY ./Pipfile ./Pipfile.lock ./

RUN pip install pipenv
RUN pipenv install --dev

CMD ["pipenv", "run", "watchmedo", "auto-restart", "--pattern", "*.py", "--recursive", "python", "main.py"]
