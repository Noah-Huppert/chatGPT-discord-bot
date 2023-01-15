FROM python:3.10

RUN mkdir -p /DiscordBot
WORKDIR /DiscordBot

COPY ./src ./src
COPY ./main.py ./main.py
COPY ./Pipfile ./Pipfile.lock ./

RUN pip install pipenv
RUN pipenv install

CMD ["pipenv", "run", "python", "main.py"]
