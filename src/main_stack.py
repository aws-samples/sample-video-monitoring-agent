# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from aws_cdk import Stack, CfnOutput
from constructs import Construct
from .constructs.storage import StorageConstruct
from .constructs.topics import TopicsConstruct
from .constructs.database import DatabaseConstruct
from .constructs.lambdas import LambdasConstruct
from .constructs.agent import AgentConstruct
import json


class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get configuration first
        config = self.get_config()

        # Create storage resources
        storage = StorageConstruct(self, "Storage", config)

        # Create SNS topics
        topics = TopicsConstruct(self, "Topics")

        # Create database resources
        database = DatabaseConstruct(
            self, "Database", storage.athena_bucket, storage.kms_key, config
        )

        # Create Lambda resources
        lambdas = LambdasConstruct(self, "Lambdas", storage, topics, database, config)

        # Create Agent (includes Knowledge Base)
        agent = AgentConstruct(
            self,
            "Agent",
            lambdas.agent_executor_lambda,
            storage.agent_assets_bucket,
            config,
        )

        # Create invoke lambda
        invoke_lambda = lambdas.create_bedrock_agent_invoke_lambda(
            agent.agent, storage.agent_assets_bucket, config
        )

        # Create update lambda
        update_lambda = lambdas.create_update_lambda(
            database.glue_crawler,
            agent.knowledge_base,
            agent.data_source,
            agent.agent,
            lambdas.agent_resource_role.role_arn,
            config,
        )

        CfnOutput(self, "StreamlitInvokeLambda", value=invoke_lambda.function_name)
        CfnOutput(self, "HighAlertTopic", value=topics.high_alert_topic.topic_arn)
        CfnOutput(self, "SoftAlertTopic", value=topics.soft_alert_topic.topic_arn)
        CfnOutput(self, "AssetsBucket", value=storage.agent_assets_bucket.bucket_name)
        CfnOutput(self, "AthenaBucket", value=storage.athena_bucket.bucket_name)

    def get_config(self):
        """Get configuration from context"""

        # read in agent_config.json
        with open("agent_config.json", "r") as f:
            config = json.load(f)

        # Store config values as instance variables
        self.ASSETS_FOLDER_NAME = config["paths"]["assets_folder_name"]
        self.ATHENA_DATA_DESTINATION_PREFIX = config["paths"][
            "athena_data_destination_prefix"
        ]
        self.ATHENA_TABLE_DATA_PREFIX = config["paths"]["athena_table_data_prefix"]
        self.KNOWLEDGEBASE_DESTINATION_PREFIX = config["paths"][
            "knowledgebase_destination_prefix"
        ]
        self.KNOWLEDGEBASE_FILE_NAME = config["paths"]["knowledgebase_file_name"]
        self.AGENT_SCHEMA_DESTINATION_PREFIX = config["paths"][
            "agent_schema_destination_prefix"
        ]

        self.BEDROCK_AGENT_NAME = config["names"]["bedrock_agent_name"]
        self.BEDROCK_AGENT_ALIAS = config["names"]["bedrock_agent_alias"]
        self.STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME = config["names"][
            "streamlit_lambda_function_name"
        ]

        self.BEDROCK_AGENT_FM = config["models"]["bedrock_agent_foundation_model"]

        self.AGENT_INSTRUCTION = config["bedrock_instructions"]["agent_instruction"]
        self.ACTION_GROUP_DESCRIPTION = config["bedrock_instructions"][
            "action_group_description"
        ]
        self.KNOWLEDGEBASE_INSTRUCTION = config["bedrock_instructions"][
            "knowledgebase_instruction"
        ]

        self.LAMBDAS_SOURCE_FOLDER = config["paths"]["lambdas_source_folder"]

        return config
