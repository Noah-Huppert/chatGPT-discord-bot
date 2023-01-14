import openai
from asgiref.sync import sync_to_async

from typing import Optional

MAX_PROMPT_LENGTH = 4096

class OpenAI:
    """ API client for OpenAI.
    """
    async def create_completion(self, prompt: str) -> Optional[str]:
        """ Given a prompt use OpenAI to complete the text.
        Arguments:
        - prompt: The text fed to the OpenAI model

        Returns: The OpenAI completion or None if the model could not complete.
        """
        response = await sync_to_async(openai.Completion.create)(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.7,
            max_tokens=2048,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )

        non_empty_responses = list(filter(lambda choice: len(choice.text) > 0, response.choices))
        if len(non_empty_responses) == 0:
            # Couldn't get any completions from OpenAI
            return None

        return non_empty_responses[0].text
