# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
from datetime import datetime, timezone
from bedrock_utils import create_multimodal_prompt, invoke_bedrock_model
import boto3

from connections import Connections
from prompt_templates import ANALYZE_GRID_SYSTEM_PROMPT, ANALYZE_GRID_AGENT_PROMPT

logger = Connections.logger
# instantiating the Bedrock client, and passing in the CLI profile
boto3.setup_default_session(profile_name=os.getenv("profile_name"))
bedrock = boto3.client(
    "bedrock-runtime",
    Connections.region_name,
    endpoint_url=f"https://bedrock-runtime.{Connections.region_name}.amazonaws.com",
)


def image_to_text(image: bytes, content_type: str, monitoring_instructions) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    logger.debug(f"process image timestamp: {timestamp}")
    text = ANALYZE_GRID_AGENT_PROMPT.format(
        monitoring_instruction=monitoring_instructions, timestamp=timestamp
    )
    prompt = create_multimodal_prompt(
        image_data=image,
        text=text,
        content_type=content_type,
        system_prompt=ANALYZE_GRID_SYSTEM_PROMPT,
        temperature=0.5,
    )

    logger.info(f"Image prompt: {text}")
    # invoking Claude3, passing in our prompt
    return invoke_bedrock_model(
        prompt=prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"
    )
