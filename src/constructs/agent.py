# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from cdklabs.generative_ai_cdk_constructs import bedrock as bedrock_constructs
from constructs import Construct
import os


class AgentConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        agent_executor_lambda,
        asset_bucket,
        config,
        **kwargs,
    ):
        super().__init__(scope, id)

        # Create knowledge base first
        self.knowledge_base, self.data_source = self._create_knowledge_base(
            asset_bucket, config
        )

        # Then create agent and associate knowledge base
        self.agent = self._create_agent(
            agent_executor_lambda, self.knowledge_base, config
        )

    def _create_knowledge_base(self, asset_bucket, config):
        kb_name = "BedrockKnowledgeBase"

        knowledge_base = bedrock_constructs.VectorKnowledgeBase(
            self,
            "BedrockOpenSearchKnowledgeBase",
            name=kb_name,
            embeddings_model=bedrock_constructs.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_256,
            instruction=config["bedrock_instructions"]["knowledgebase_instruction"],
        )

        data_source = bedrock_constructs.S3DataSource(
            self,
            "DataSource",
            bucket=asset_bucket,
            knowledge_base=knowledge_base,
            data_source_name="books",
            inclusion_prefixes=[
                f"{config['paths']['knowledgebase_destination_prefix']}/"
            ],
            chunking_strategy=bedrock_constructs.ChunkingStrategy.FIXED_SIZE,
        )

        return knowledge_base, data_source
    
    # https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/apidocs/%40cdklabs/namespaces/bedrock/classes/BedrockFoundationModel.md
    def _create_agent(self, agent_executor_lambda, knowledge_base, config):
        agent = bedrock_constructs.Agent(
            self,
            "Agent",
           foundation_model=bedrock_constructs.BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0,
            instruction=config["bedrock_instructions"]["agent_instruction"],
        )

        agent.add_knowledge_base(knowledge_base)

        action_group = bedrock_constructs.AgentActionGroup(
            name="action-group",
            description=config["bedrock_instructions"]["action_group_description"],
            executor=bedrock_constructs.ActionGroupExecutor.fromlambda_function(
                agent_executor_lambda
            ),
            enabled=True,
            api_schema=bedrock_constructs.ApiSchema.from_local_asset(
                os.path.join(
                    os.getcwd(),
                    config["paths"]["assets_folder_name"],
                    "agent_api_schema/artifacts_schema.json",
                )
            ),
        )

        agent.add_action_group(action_group)
        return agent
