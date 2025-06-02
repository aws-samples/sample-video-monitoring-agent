# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
from logging import DEBUG, INFO

import boto3
import botocore
from aws_lambda_powertools import Logger
from mypy_boto3_lambda import LambdaClient
from mypy_boto3_s3 import S3Client

from utils import get_stack_outputs

session = boto3.Session()

if os.environ.get("ACCOUNT_ID") is None:
    ACCOUNT_ID = session.client("sts").get_caller_identity().get("Account")
    AWS_REGION = session.region_name
else:
    ACCOUNT_ID = os.environ["ACCOUNT_ID"]
    AWS_REGION = os.environ["AWS_REGION"]

STACK_NAME = os.environ.get("STACK_NAME", "chatbot-stack")
S3_PREFIX = os.environ.get("S3_PREFIX", "captures")


class Connections:
    logger = Logger(level=INFO)

    s3_prefix = S3_PREFIX
    sns_client = boto3.client("sns")
    cfn_client = boto3.client("cloudformation")

    stack_outputs = get_stack_outputs(STACK_NAME, cfn_client)
    logger.info(f"stack outputs {stack_outputs}")

    lambda_function_name = stack_outputs["StreamlitInvokeLambda"]

    # This is a workaround for the pickle multiprocessing issue
    @staticmethod
    def s3_client_provider() -> S3Client:
        return boto3.client("s3")

    @staticmethod
    def lambda_client_provider() -> LambdaClient:
        return boto3.client(
            "lambda",
            region_name=AWS_REGION,
            config=botocore.config.Config(read_timeout=300, connect_timeout=300),
        )
