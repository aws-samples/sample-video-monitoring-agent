# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from aws_cdk import (
    aws_sns as sns,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class TopicsConstruct(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id)

        self.high_alert_topic = self._create_topic("high_alert_topic")
        self.soft_alert_topic = self._create_topic("soft_alert_topic")

    def _create_topic(self, topic_name):
        topic = sns.Topic(
            self,
            topic_name,
            display_name=topic_name,
        )

        topic.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["sns:Publish"],
                principals=[iam.AnyPrincipal()],
                resources=[topic.topic_arn],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            )
        )

        return topic
