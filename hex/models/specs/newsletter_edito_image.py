from pydantic import BaseModel, Field

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.openai_image_config import OpenAIImageConfig


class NewsletterEditoImageInput(BaseModel):
    """Schema for the input data to generate an editorial image."""
    title: str = Field(
        ..., description="The editorial text to inspire the image generation"
    )

class NewsletterEditoImageOutput(BaseModel):
    """Schema for the output image."""
    edito: str = Field(
        ..., description="The editorial text to inspire the image generation"
    )

NEWSLETTER_EDITO_IMAGE_PROMPT = PromptTemplateSpec(
    name="edito_image_prompt",
    version="v1.0.0",
    description="Generate a digital illustration for the Hex Machina newsletter editorial.",
    input_schema=NewsletterEditoImageInput,
    output_schema=NewsletterEditoImageOutput,
    template="""
An abstract, conceptual digital illustration representing the theme: "{title}".

Futuristic and minimalist visual style.  
Cool blue and white palette.  
Soft gradients on a light background.  
Wide horizontal format (banner-style).  
Centered, balanced composition.  
Evokes intelligence, signal flow, and machine coordination.  
**Do not include any text, words, or lettering in the image.**
"""
)

TAGGER_SPEC = ModelSpec(
    name="edito_image_spec",
    version="v1",
    description="Generate an image for the Hex Machina newsletter editorial.",
    provider="openai_image",
    config=OpenAIImageConfig(
        prompt_spec=NEWSLETTER_EDITO_IMAGE_PROMPT,
        model="dall-e-3",
        size="1792x1024",
        quality="hd",
        api_key_env_var="OPENAI_API_KEY",
        response_format="b64_json",
        n=1
    )

)
