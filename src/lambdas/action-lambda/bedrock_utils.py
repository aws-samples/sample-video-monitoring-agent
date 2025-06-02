# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import json
import logging
import base64
from typing import Dict, Any
from connections import Connections

logger = Connections.logger


def invoke_bedrock_model(
    prompt: Dict[str, Any],
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    max_tokens: int = 1000,
    temperature: float = 0.5,
) -> str:
    """
    Invoke Bedrock model with given prompt and return the response text.

    Args:
        prompt: Dictionary containing the prompt structure
        model_id: Bedrock model ID to use
        max_tokens: Maximum tokens for response
        temperature: Temperature for response generation

    Returns:
        str: Model's response text
    """
    try:
        logger.info(f"Prompt for Bedrock: {prompt}")

        response = Connections.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(prompt),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response.get("body").read())
        logger.info(f"Bedrock response: {response_body}")

        analysis = response_body["content"][0]["text"]
        logger.info(f"Bedrock analysis: {analysis}")

        return analysis

    except Exception as e:
        logger.error(f"Error invoking Bedrock: {e}")
        raise


def create_text_prompt(
    content: str,
    system_prompt: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.5,
) -> Dict[str, Any]:
    """Create a text-only prompt structure"""
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": content}],
    }
    if system_prompt:
        prompt["system"] = system_prompt
    return prompt


def create_multimodal_prompt(
    image_data: bytes,
    text: str,
    content_type: str,
    system_prompt: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.5,
) -> Dict[str, Any]:
    """Create a multimodal prompt structure with image and text"""
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": base64.b64encode(image_data).decode("utf-8"),
                        },
                    },
                    {"type": "text", "text": text},
                ],
            }
        ],
    }
    if system_prompt:
        prompt["system"] = system_prompt
    return prompt
