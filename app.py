#!/usr/bin/env python3

# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.


import os
import aws_cdk as cdk
import cdk_nag
import json
from src.main_stack import MainStack
from cdk_nag import NagSuppressions
from aws_cdk import Aspects

app = cdk.App()

with open("agent_config.json", encoding="utf-8") as f:
    config = json.load(f)

stack_name = config["names"]["stack_name"]

appStack = MainStack(
    app,
    stack_name,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

Aspects.of(appStack).add(cdk_nag.AwsSolutionsChecks())

NagSuppressions.add_stack_suppressions(
    appStack,
    suppressions=[
        {"id": "AwsSolutions-IAM5", "reason": "Dynamic resource creation"},
        {
            "id": "AwsSolutions-IAM4",
            "reason": "Managed policies are used for log stream access",
        },
        {
            "id": "AwsSolutions-L1",
            "reason": "Lambda auto-created by CDK library construct",
        },
    ],
)

app.synth()
