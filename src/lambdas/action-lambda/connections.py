# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
import boto3
from aws_lambda_powertools import Logger
from llama_index.llms.bedrock import Bedrock


class Connections:
    logger = Logger()
    region_name = os.environ["AWS_REGION"]
    athena_bucket_name = os.environ["ATHENA_BUCKET_NAME"]
    agent_bucket_name = os.environ["AGENT_BUCKET_NAME"]
    text2sql_database = os.environ["TEXT2SQL_DATABASE"]
    log_level = os.environ["LOG_LEVEL"]
    soft_alert_topic = os.environ["SOFT_ALERT_TOPIC_ARN"]
    high_alert_topic = os.environ["HIGH_ALERT_TOPIC_ARN"]
    knowledgebase_destination_prefix = os.environ["KNOWLEDGEBASE_DESTINATION_PREFIX"]

    #####

    s3_resource = boto3.resource("s3", region_name=region_name)
    s3_client = boto3.client("s3", region_name=region_name)
    sns_client = boto3.client("sns", region_name=region_name)
    bedrock_client = boto3.client("bedrock-runtime", region_name=region_name)

    @staticmethod
    def get_bedrock_llm(model_name="Claude3", max_tokens=256):
        MODELID_MAPPING = {
            "Titan": "amazon.titan-tg1-large",
            "Jurassic": "ai21.j2-ultra-v1",
            "Claude2": "anthropic.claude-v2",
            #
            "Claude3.5": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "Claude3": "anthropic.claude-3-sonnet-20240229-v1:0",
            "ClaudeInstant": "anthropic.claude-instant-v1",
        }

        MODEL_KWARGS_MAPPING = {
            "Titan": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Jurassic": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Claude2": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Claude3": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Claude3.5": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "ClaudeInstant": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
        }
        model_kwargs = MODEL_KWARGS_MAPPING[model_name].copy()
        model_kwargs = MODEL_KWARGS_MAPPING[model_name].copy()

        model_kwargs.update(
            {
                "model": MODELID_MAPPING[model_name],
                "aws_region_name": Connections.region_name,
            }
        )

        llm = Bedrock(**model_kwargs)

        return llm
