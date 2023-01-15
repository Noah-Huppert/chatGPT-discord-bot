import openai
from asgiref.sync import sync_to_async
from transformers import GPT2TokenizerFast

from typing import Optional

# Maximum number of tokens the GPT3 model can work with, including input and output (https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them)
GPT3_MAX_TOKENS = 4096

# Maximum number of tokens which can be sent as a prompt.
MAX_PROMPT_LENGTH = GPT3_MAX_TOKENS / 2

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
    - tokenizer: Used to convert strings into GPT3 tokens
    """
    api_key: str
    prompt_tokenizer: GPT2TokenizerFast

    def __init__(self, api_key: str):
        """ Initializes.
        """
        self.api_key= api_key
        self.prompt_tokenizer = GPT2TokenizerFast.from_pretrained("gpt2", max_length=MAX_PROMPT_LENGTH)
    
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
            if e.http_status == 400 and e.http_body is not None and isinstance(e.http_body, str) and ERR_BODY_COMPLETION_MAX_LENGTH in e.http_body:
                raise CompletionPromptTooLong() from e
            else:
                raise e


        non_empty_responses = list(filter(lambda choice: len(choice.text) > 0, response.choices))
        if len(non_empty_responses) == 0:
            # Couldn't get any completions from OpenAI
            return None

        return non_empty_responses[0].text
