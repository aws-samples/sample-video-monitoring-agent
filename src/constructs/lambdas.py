# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    custom_resources as cr,
    CustomResource,
    Duration,
    Size,
    Aws,
)
from aws_cdk.aws_ecr_assets import Platform
from constructs import Construct


class LambdasConstruct(Construct):
    def __init__(
        self, scope: Construct, id: str, storage, topics, database, config, **kwargs
    ):
        super().__init__(scope, id)

        self.powertools_layer = self._get_powertools_layer()

        self.agent_resource_role = self._create_agent_execution_role(
            storage.agent_assets_bucket
        )

        self.agent_executor_lambda = self._create_agent_executor_lambda(
            storage.agent_assets_bucket,
            storage.athena_bucket,
            storage.kms_key,
            database.glue_database,
            config["logging"],
            topics.soft_alert_topic,
            topics.high_alert_topic,
            config,
        )

    def _get_powertools_layer(self):

        POWERTOOLS_LAYER_ARN: str = (
            f"arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV2:67"
        )
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, id="PowertoolsLayer", layer_version_arn=POWERTOOLS_LAYER_ARN
        )
        return powertools_layer

    def _create_agent_execution_role(self, agent_assets_bucket):
        agent_resource_role = iam.Role(
            self,
            "ChatBotBedrockAgentRole",
            role_name="AmazonBedrockExecutionRoleForAgents_chatbot",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        agent_assets_bucket.grant_read(agent_resource_role)

        # Keep Bedrock policies as they don't have grant APIs
        agent_resource_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{Aws.REGION}::foundation-model/*"],
            )
        )

        agent_resource_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*"
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{Aws.ACCOUNT_ID}",
                    },
                },
            )
        )

        return agent_resource_role

    def _create_agent_executor_lambda(
        self,
        agent_assets_bucket,
        athena_bucket,
        kms_key,
        glue_database,
        logging_context,
        soft_alert_topic,
        high_alert_topic,
        config,
    ):
        ecr_image = lambda_.EcrImageCode.from_asset_image(
            directory=os.path.join(
                os.getcwd(), config["paths"]["lambdas_source_folder"], "action-lambda"
            ),
            platform=Platform.LINUX_AMD64,
        )

        lambda_role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonAthenaFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ],
        )

        soft_alert_topic.grant_publish(lambda_role)
        high_alert_topic.grant_publish(lambda_role)

        lambda_function = lambda_.Function(
            self,
            "AgentActionLambdaFunction",
            function_name=f"{Aws.STACK_NAME}-agent-action-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code for GenAI Chatbot",
            architecture=lambda_.Architecture.X86_64,
            handler=lambda_.Handler.FROM_IMAGE,
            runtime=lambda_.Runtime.FROM_IMAGE,
            code=ecr_image,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "ATHENA_BUCKET_NAME": athena_bucket.bucket_name,
                "AGENT_BUCKET_NAME": agent_assets_bucket.bucket_name,
                "TEXT2SQL_DATABASE": glue_database.ref,
                "LOG_LEVEL": logging_context["lambda_log_level"],
                "SOFT_ALERT_TOPIC_ARN": soft_alert_topic.topic_arn,
                "HIGH_ALERT_TOPIC_ARN": high_alert_topic.topic_arn,
                "KNOWLEDGEBASE_DESTINATION_PREFIX": config["paths"][
                    "knowledgebase_destination_prefix"
                ],
            },
            environment_encryption=kms_key,
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=4096,
            ephemeral_storage_size=Size.mebibytes(4096),
        )

        lambda_function.add_permission(
            "BedrockLambdaInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=Aws.ACCOUNT_ID,
            source_arn=f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
        )

        agent_assets_bucket.grant_read_write(lambda_role)
        athena_bucket.grant_read_write(lambda_role)

        return lambda_function

    def create_bedrock_agent_invoke_lambda(self, agent, agent_assets_bucket, config):
        invoke_lambda_role = iam.Role(
            self,
            "InvokeLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Lambda to access Bedrock agents and S3",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        invoke_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListAgents",
                    "bedrock:ListAgentAliases",
                    "bedrock:InvokeAgent",
                ],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/{agent.agent_id}",
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/{agent.agent_id}/*",
                ],
            )
        )

        agent_assets_bucket.grant_read_write(invoke_lambda_role)

        invoke_lambda = lambda_.Function(
            self,
            config["names"]["streamlit_lambda_function_name"],
            function_name=f"{Aws.STACK_NAME}-{config['names']['streamlit_lambda_function_name']}-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(
                    os.getcwd(),
                    config["paths"]["lambdas_source_folder"],
                    "invoke-lambda",
                )
            ),
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "AGENT_ID": agent.agent_id,
                "REGION_NAME": Aws.REGION,
                "ASSET_BUCKET_NAME": agent_assets_bucket.bucket_name,
            },
            layers=[self.powertools_layer],
            role=invoke_lambda_role,
            timeout=Duration.minutes(15),
        )

        invoke_lambda.add_permission(
            "AllowS3Invocation",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=agent_assets_bucket.bucket_arn,
        )

        return invoke_lambda

    def create_update_lambda(
        self,
        glue_crawler,
        knowledge_base,
        data_source,
        agent,
        agent_resource_role_arn,
        config,
    ):
        lambda_role = iam.Role(
            self,
            "LambdaRole_update_resources",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
            ],
        )

        glue_crawler_policy = iam.Policy(
            self,
            "TriggerGlueCrawlerPolicy",
            policy_name="allow_trigger_glue_crawler_policy",
            statements=[
                iam.PolicyStatement(
                    actions=["glue:GetCrawler", "glue:StartCrawler"],
                    resources=[
                        f"arn:aws:glue:{Aws.REGION}::crawler/{glue_crawler.name}"
                    ],
                    effect=iam.Effect.ALLOW,
                )
            ],
        )

        bedrock_policy = iam.Policy(
            self,
            "BedrockAgent_KB_Update_Policy",
            policy_name="allow_update_bedrock_agent_kb_policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "bedrock:StartIngestionJob",
                        "bedrock:UpdateAgentKnowledgeBase",
                        "bedrock:GetAgentAlias",
                        "bedrock:UpdateKnowledgeBase",
                        "bedrock:UpdateAgent",
                        "bedrock:GetIngestionJob",
                        "bedrock:CreateAgentAlias",
                        "bedrock:UpdateAgentAlias",
                        "bedrock:GetAgent",
                        "bedrock:PrepareAgent",
                        "bedrock:DeleteAgentAlias",
                        "bedrock:DeleteAgent",
                        "bedrock:ListAgentAliases",
                    ],
                    resources=[
                        f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
                        f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/*",
                        f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*",
                    ],
                    effect=iam.Effect.ALLOW,
                )
            ],
        )

        lambda_role.attach_inline_policy(glue_crawler_policy)
        lambda_role.attach_inline_policy(bedrock_policy)

        update_lambda_function = lambda_.Function(
            self,
            "LambdaFunction_update_resources",
            function_name=f"{Aws.STACK_NAME}-update-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code to trigger crawler, create bedrock agent alias, knowledgebase data sync",
            architecture=lambda_.Architecture.ARM_64,
            handler="lambda_handler.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(
                os.path.join(
                    os.getcwd(),
                    config["paths"]["lambdas_source_folder"],
                    "update-lambda",
                )
            ),
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "GLUE_CRAWLER_NAME": glue_crawler.name,
                "KNOWLEDGEBASE_ID": knowledge_base.knowledge_base_id,
                "KNOWLEDGEBASE_DATASOURCE_ID": data_source.data_source_id,
                "BEDROCK_AGENT_ID": agent.agent_id,
                "BEDROCK_AGENT_NAME": config["names"]["bedrock_agent_name"],
                "BEDROCK_AGENT_ALIAS": config["names"]["bedrock_agent_alias"],
                "BEDROCK_AGENT_RESOURCE_ROLE_ARN": agent_resource_role_arn,
                "LOG_LEVEL": "info",
            },
            layers=[self.powertools_layer],
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
        )

        provider = cr.Provider(
            self,
            "LambdaUpdateResourcesCustomProvider",
            on_event_handler=update_lambda_function,
        )

        CustomResource(
            self,
            "LambdaUpdateResourcesCustomResource",
            service_token=provider.service_token,
        )

        return update_lambda_function
