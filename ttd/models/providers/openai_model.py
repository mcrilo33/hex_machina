import copy
from openai import OpenAI
from ttd.models.base_model import BaseModel


class OpenAIModel(BaseModel):
    def __init__(self, config: dict):
        super().__init__(config)
        for key in ["api_key", "base_url", "model_name"]:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        api_key = config["api_key"]
        self.client = OpenAI(base_url=config["base_url"], api_key=api_key)

        chat_completions_params = copy.deepcopy(config)
        for k in ["api_key", "base_url", "model_name", "prompt"]:
            del chat_completions_params[k]
        self.chat_completions_params = chat_completions_params

    def predict(self, input_data: dict) -> dict:
        response = self.client.chat.completions.create(
            model=self.config["model_name"],
            messages=[{"role": "user", "content": self.prompt(**input_data)}],
            **self.chat_completions_params
        )

        if hasattr(response, 'error'):
            provider = response.error.get("metadata", {}).get('provider_name', 'Unknown provider').upper()
            raise ValueError(f"PROVIDER [[{provider}]]\n== Error {response.error.get('code')}: {response.error.get('message')}")


        return {
            "output": response.choices[0].message.content.strip(),
            "metadata": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }
