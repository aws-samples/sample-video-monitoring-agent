# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from connections import Connections
from utils import wait_for_state

logger = Connections.logger


def check_ingestion_job_state(
    bedrock_agent, knowledgebase_id, data_source_id, ingestion_job_id
):
    """
    Checks the current state of the ingestion job.

    Args:
        bedrock_agent: The Bedrock Agent client.
        knowledgebase_id (str): The Knowledgebase ID.
        data_source_id (str): The Data Source ID.
        ingestion_job_id (str): The Ingestion Job ID.

    Returns:
        The current ingestion job state.
    """
    response = bedrock_agent.get_ingestion_job(
        knowledgeBaseId=knowledgebase_id,
        dataSourceId=data_source_id,
        ingestionJobId=ingestion_job_id,
    )
    return response["ingestionJob"]["status"]


def trigger_data_source_sync(bedrock_agent, knowledgebase_id, data_source_id):
    """
    Trigger the "Data Source" Sync step after Knowledgebase is created.

    Args:
        bedrock_agent (BedrockAgent): The Bedrock Agent instance.
        knowledgebase_id (str): The ID of the Knowledgebase.
        data_source_id (str): The ID of the Data Source.

    Returns:
        None.
    """
    # Start the ingestion job.
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=knowledgebase_id, dataSourceId=data_source_id
    )
    ingestion_job_id = response["ingestionJob"]["ingestionJobId"]

    try:
        # Wait for the ingestion job to reach the "COMPLETE" state.
        final_state = wait_for_state(
            check_fn=check_ingestion_job_state,
            resource_identifier="Trigger Data Source Sync",
            expected_state="COMPLETE",
            waiting_states=["STARTING", "IN_PROGRESS"],
            bedrock_agent=bedrock_agent,
            knowledgebase_id=knowledgebase_id,
            data_source_id=data_source_id,
            ingestion_job_id=ingestion_job_id,
        )
        logger.info(
            f"The Knowledgebase ingestion job {ingestion_job_id} completed successfully with state {final_state}."
        )
    except Exception as e:
        logger.error(f"Ingestion job {ingestion_job_id} failed with error: {e}")
        raise
