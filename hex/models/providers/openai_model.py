import re
from openai import OpenAI
from pydantic import BaseModel


class PromptTemplate:
    """ A class to represent a prompt template with placeholders. """
    def __init__(self, prompt_spec: dict):
        self.prompt_spec = prompt_spec
        self.template = prompt_spec.template
        self.placeholders = self._extract_placeholders()

    def _extract_placeholders(self):
        return set(re.findall(r"{([\w]+)}", self.template))

    def __call__(self, **kwargs):
        missing = self.placeholders - kwargs.keys()
        if missing:
            raise ValueError(f"Missing values for placeholders: {missing}")
        return self.template.format(**kwargs)

    def __repr__(self):
        return f"<PromptTemplate(name={self.prompt_spec.name}, " + \
               f"placeholders={self.placeholders})>"


class OpenAIModel():
    """ A class to represent an OpenAI model. """
    def __init__(self, config: BaseModel):
        self.prompt = PromptTemplate(config.prompt_spec)
        self.client = OpenAI(base_url=config.base_url,
                             api_key=config.api_key)
        self.config = config

        chat_completions_params = {}
        for k in ["temperature", "max_tokens", "n"]:
            chat_completions_params[k] = getattr(config, k, None)
        self.chat_completions_params = chat_completions_params

    def predict(self, input_data: dict) -> dict:
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=[{"role": "user", "content": self.prompt(**input_data)}],
            **self.chat_completions_params
        )

        if hasattr(response, 'error'):
            provider = response.error.get(
                "metadata", {}
            ).get('provider_name', 'Unknown provider')
            raise ValueError(
                f"PROVIDER [[{provider}]]\n== Error {response.error.get('code')}: " +
                f"{response.error.get('message')}"
            )

        return {
            "output": response.choices[0].message.content.strip(),
            "metadata": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }


class OpenAIImageModel:
    """A class to represent an OpenAI image generation model."""
    def __init__(self, config: BaseModel):
        self.prompt = PromptTemplate(config.prompt_spec)
        self.client = OpenAI(api_key=config.api_key)
        self.config = config
        print(f"OpenAIImageModel initialized with config: {config}")
        image_params = {}
        for k in ["model", "n", "size", "quality", "response_format"]:
            image_params[k] = getattr(config, k, None)
        self.image_params = image_params

    def predict(self, input_data: dict) -> dict:
        params = self.image_params.copy()
        prompt_str = self.prompt(**input_data)
        params["prompt"] = prompt_str
        response = self.client.images.generate(**params)
        if hasattr(response, 'error'):
            provider = response.error.get(
                "metadata", {}
            ).get('provider_name', 'Unknown provider')
            raise ValueError(
                f"PROVIDER [[{provider}]]\n== Error {response.error.get('code')}: " +
                f"{response.error.get('message')}"
            )
        images_b64 = [img.b64_json for img in response.data]
        return {
            "output": images_b64,
            "metadata": {
                "model": params.get(
                    "model",
                    self.config.model_name if hasattr(
                        self.config, "model_name"
                    ) else None
                ),
                "n": params.get("n", 1),
                "size": params.get("size"),
                "quality": params.get("quality"),
                "response_format": params.get("response_format"),
            },
        }
