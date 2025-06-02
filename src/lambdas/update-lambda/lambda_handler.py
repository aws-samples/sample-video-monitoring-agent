# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from trigger_glue_crawler import trigger_glue_crawler
from trigger_data_source_sync import trigger_data_source_sync
from prepare_agent import prepare_bedrock_agent
from connections import Connections
from aws_lambda_powertools import Tracer

# Set up logging
logger = Connections.logger
tracer = Tracer()

glue_client = Connections.glue_client
bedrock_agent = Connections.bedrock_agent
agent_id = Connections.agent_id
agent_alias_name = Connections.agent_alias_name
data_source_id = Connections.data_source_id
knowledgebase_id = Connections.knowledgebase_id
crawler_name = Connections.crawler_name


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        request_type = event["RequestType"]

        if request_type == "Create":
            return on_create(event)
        elif request_type == "Delete":
            return on_delete(event)
        elif request_type == "Update":
            return on_update(event)
        else:
            raise ValueError(f"Invalid request type: {request_type}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise  # Let the framework handle the error


def on_create(event):
    # Generate a physical ID for the resource
    physical_id = f"agent-setup-{event['RequestId']}"

    try:
        # Trigger Glue Crawler
        logger.info("Starting Glue Crawler trigger.")
        trigger_glue_crawler(glue_client, crawler_name)

        # Trigger Data Source Sync
        logger.info("Starting Data Source Sync.")
        trigger_data_source_sync(bedrock_agent, knowledgebase_id, data_source_id)

        # Prepare Bedrock Agent
        logger.info("Starting Preparing Bedrock Agent.")
        prepare_bedrock_agent(bedrock_agent, agent_id, agent_alias_name)

        # Create Agent Alias
        logger.info("Creating Agent Alias.")
        prepare_bedrock_agent(
            bedrock_agent, agent_id, agent_alias_name, create_alias=True
        )

        return {
            "PhysicalResourceId": physical_id,
            "Data": {"AgentId": agent_id, "Status": "SUCCESS"},
        }
    except Exception as e:
        logger.error(f"Create failed: {e}")
        raise


def on_delete(event):
    # Use the existing physical ID
    physical_id = event["PhysicalResourceId"]

    try:
        response = bedrock_agent.list_agent_aliases(agentId=agent_id)
        alias_ids = [
            summary["agentAliasId"] for summary in response["agentAliasSummaries"] if summary["agentAliasId"] != "TSTALIASID"
        ]

        for agent_alias_id in alias_ids:
            logger.info(f"Deleting Agent Alias: {agent_alias_id}")
            bedrock_agent.delete_agent_alias(
                agentId=agent_id, agentAliasId=agent_alias_id
            )

        bedrock_agent.delete_agent(agentId=agent_id, skipResourceInUseCheck=False)

        return {"PhysicalResourceId": physical_id}
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise


def on_update(event):
    # Use the existing physical ID
    physical_id = event["PhysicalResourceId"]

    # If no update logic needed, just return the physical ID
    return {"PhysicalResourceId": physical_id, "Data": {"Status": "NO_UPDATE_NEEDED"}}
