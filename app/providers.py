"""Explicit providers: no silent fallback, no credentials in traces."""
import json
import os
import time
from openai import OpenAI
from pydantic import BaseModel


class Model:
    def __init__(self, provider=None, model=None):
        self.provider = provider or os.getenv("EVIDENCE_PROVIDER", "openai")
        self.model = model or (os.getenv("BEDROCK_MODEL_ID", "") if self.provider == "bedrock" else os.getenv("EVIDENCE_MODEL", "gpt-4.1-mini"))
        self.usage = []
        if self.provider == "openai":
            self.client = OpenAI(timeout=70, max_retries=1)
        elif self.provider == "bedrock":
            import boto3
            if not self.model:
                raise ValueError("Set BEDROCK_MODEL_ID to an enabled model or inference profile.")
            self.client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        else:
            raise ValueError("Unsupported model provider")

    def structured(self, system: str, payload: dict, schema: type[BaseModel]):
        started = time.monotonic()
        system += "\nReturn only a JSON object matching this schema: " + json.dumps(schema.model_json_schema())
        message = json.dumps(payload, ensure_ascii=False)
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=2600,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
            )
            text = response.choices[0].message.content
            usage = {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens}
        else:
            response = self.client.converse(
                modelId=self.model, system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": message}]}],
                inferenceConfig={"temperature": 0, "maxTokens": 2600},
            )
            text = "".join(item.get("text", "") for item in response["output"]["message"]["content"])
            usage = {"input_tokens": response.get("usage", {}).get("inputTokens", 0), "output_tokens": response.get("usage", {}).get("outputTokens", 0)}
        self.usage.append({"stage": schema.__name__, **usage, "seconds": round(time.monotonic()-started, 3)})
        if text.strip().startswith("```"):
            text = text.strip().split("\n", 1)[1].rsplit("```", 1)[0]
        return schema.model_validate_json(text)
