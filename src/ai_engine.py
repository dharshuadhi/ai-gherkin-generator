"""AI engine: generate Gherkin via Azure OpenAI.

Requires:
    AZURE_OPENAI_ENDPOINT   e.g. https://my-resource.openai.azure.com/
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_DEPLOYMENT e.g. gpt-4o (optional, defaults to gpt-4o)
    AZURE_OPENAI_API_VERSION (optional)
"""

import os

from .prompts import SYSTEM_PROMPT


def _client():
    try:
        from openai import AzureOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required for the AI engine. "
            "Install it with: pip install -r requirements.txt"
        ) from exc

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError(
            "AI engine needs AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY. "
            "Copy .env.example to .env and fill in your values, "
            "or use --engine rule for the offline generator."
        )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )


def generate_with_ai(story_text: str, deployment: str | None = None) -> str:
    """Generate a Gherkin feature file from a requirement using Azure OpenAI."""
    client = _client()
    deployment = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": story_text},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content.strip()
    # Strip accidental markdown fences so the output is a clean .feature file
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return content.strip() + "\n"
