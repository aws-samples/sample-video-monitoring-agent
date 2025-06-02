# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from connections import Connections
from utils import wait_for_state

logger = Connections.logger


def check_agent_state(bedrock_agent, agent_id, agent_alias_id):
    """
    Checks the current state of the Bedrock agent.

    Args:
        bedrock_agent: The Bedrock Agent client.
        agent_id (str): The agent ID.

    Returns:
        The current agent state.
    """
    response = bedrock_agent.get_agent(agentId=agent_id)
    return response["agent"]["agentStatus"]


def check_alias_state(bedrock_agent, agent_id, agent_alias_id=None):
    """
    Checks the current state of an agent alias.

    Args:
        bedrock_agent: The Bedrock Agent client.
        agent_id (str): The agent ID.
        agent_alias_id (str): The alias ID.

    Returns:
        The current alias state.
    """
    response = bedrock_agent.get_agent_alias(
        agentId=agent_id, agentAliasId=agent_alias_id
    )
    return response["agentAlias"]["agentAliasStatus"]


def prepare_bedrock_agent(
    bedrock_agent,
    agent_id,
    agent_alias_name,
    create_alias=False,
    alias_description="agent alias description",
):
    """
    Prepare the Bedrock agent.

    Args:
        bedrock_agent (BedrockAgent): The Amazon Bedrock Agent client object.
        agent_id (str): The ID of the agent to prepare.

    Returns:
        None
    """
    # Initiate agent preparation.
    agent_alias_id = None

    if create_alias:
        response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName=agent_alias_name,
            description=alias_description,  # A description of the alias of the agent.
        )

        # Get Agent Alias ID
        agent_alias_id = response["agentAlias"]["agentAliasId"]
        state_check_function, description = check_alias_state, "Create Agent Alias"
    else:
        response = bedrock_agent.prepare_agent(agentId=agent_id)
        state_check_function, description = check_agent_state, "Prepare Bedrock Agent"

    try:
        # Wait for the agent to reach the "PREPARED" state.
        final_state = wait_for_state(
            check_fn=state_check_function,
            resource_identifier=description,
            expected_state="PREPARED",
            waiting_states=["CREATING", "UPDATING", "PREPARING"],
            bedrock_agent=bedrock_agent,
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
        )
        logger.info(
            f"The Bedrock Agent {agent_id} is prepared successfully with state {final_state}."
        )
    except Exception as e:
        logger.error(f"Failed to prepare agent: {e}")
        raise
