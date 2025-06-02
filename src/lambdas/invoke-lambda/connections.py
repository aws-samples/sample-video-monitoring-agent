# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
import boto3
from aws_lambda_powertools import Logger


class Connections:
    logger = Logger()
    agent_id = os.environ["AGENT_ID"]
    REGION_NAME = os.environ["REGION_NAME"]

    asset_bucket_name = os.environ["ASSET_BUCKET_NAME"]
    agent_client = boto3.client("bedrock-agent", region_name=REGION_NAME)
    agent_runtime_client = boto3.client(
        "bedrock-agent-runtime", region_name=REGION_NAME
    )
    s3_resource = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
