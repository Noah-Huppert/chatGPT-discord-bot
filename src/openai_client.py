import openai
from asgiref.sync import sync_to_async

from typing import Optional

# Maximum number of tokens (https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them) which can be sent as a prompt.
MAX_PROMPT_LENGTH = 4096

# OpenAI response body which indicates the prompt was too long.
ERR_BODY_COMPLETION_MAX_LENGTH = "Please reduce your prompt; or completion length"

class CompletionPromptTooLong(Exception):
    """ Indicates the prompt provided to the OpenAI completion endpoint, along with the length of the model's response, exceeded the model's maximum token length.
    To fix this the prompt's length must be reduced.
    """
    def __init__(self) -> None:
        super().__init__("Prompt too long")

class OpenAI:
    """ API client for OpenAI.
    Fields:
    - api_key: OpenAI API key
    """
    api_key: str

    def __init__(self, api_key: str):
        """ Initializes.
        """
        self.api_key= api_key
    
    async def create_completion(self, prompt: str) -> Optional[str]:
        """ Given a prompt use OpenAI to complete the text.
        Arguments:
        - prompt: The text fed to the OpenAI model

        Returns: The OpenAI completion or None if the model could not complete.
        """
        response = None

        try:
            response = await sync_to_async(openai.Completion.create)(
                api_key=self.api_key,
                model="text-davinci-003",
                prompt=prompt,
                temperature=0.7,
                max_tokens=2048, # No. of tokens to generate
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
        except openai.InvalidRequestError as e:
            # Detect if we hit the max token error
            if e.http_status == 400 and ERR_BODY_COMPLETION_MAX_LENGTH in e.http_body:
                raise CompletionPromptTooLong() from e


        non_empty_responses = list(filter(lambda choice: len(choice.text) > 0, response.choices))
        if len(non_empty_responses) == 0:
            # Couldn't get any completions from OpenAI
            return None

        return non_empty_responses[0].text
