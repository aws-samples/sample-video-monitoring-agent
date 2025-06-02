# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from connections import Connections
import json
import logging
import re
import time
from datetime import datetime, timezone
from aws_lambda_powertools import Tracer


logger = Connections.logger
tracer = Tracer()


def get_highest_agent_version_alias_id(response):
    """
    Find newest agent alias id.

    Args:
        response (dict): Response from list_agent_aliases().

    Returns:
        str: Agent alias ID of the newest agent version.
    """
    # Initialize highest version info
    highest_version = None
    highest_version_alias_id = None

    # Iterate through the agentAliasSummaries
    for alias_summary in response.get("agentAliasSummaries", []):
        # Assuming each alias has one routingConfiguration
        if alias_summary["routingConfiguration"]:
            agent_version = alias_summary["routingConfiguration"][0]["agentVersion"]
            # Check if the version is numeric and higher than the current highest
            if agent_version.isdigit() and (
                highest_version is None or int(agent_version) > highest_version
            ):
                highest_version = int(agent_version)
                highest_version_alias_id = alias_summary["agentAliasId"]

    # Return the highest version alias ID or None if not found
    return highest_version_alias_id


def invoke_agent(user_input, session_id):
    """
    Get response from Agent
    """
    response = Connections.agent_client.list_agent_aliases(agentId=Connections.agent_id)

    logger.info(f"list_agent_aliases: {response}")
    agent_alias_id = get_highest_agent_version_alias_id(response)
    if not agent_alias_id:
        return "No agent published alias found - cannot invoke agent"
    streaming_response = Connections.agent_runtime_client.invoke_agent(
        agentId=Connections.agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        enableTrace=True,
        inputText=user_input,
    )

    return streaming_response


def get_agent_response(response):
    logger.info(f"Getting agent response... {response}")
    if "completion" not in response:
        return f"No completion found in response: {response}"
    trace_list = []
    for event in response["completion"]:
        logger.info(f"Event keys: {event.keys()}")
        if "trace" in event:
            logger.info(event["trace"])
            trace_list.append(event["trace"])

        # Extract the traces
        if "chunk" in event:
            # Extract the bytes from the chunk
            chunk_bytes = event["chunk"]["bytes"]

            # Convert bytes to string, assuming UTF-8 encoding
            chunk_text = chunk_bytes.decode("utf-8")

            # Print the response text
            logger.info("Response from the agent:", chunk_text)

            # If there are citations with more detailed responses, print them
            reference_text = ""
            source_file_list = []
            if (
                "attribution" in event["chunk"]
                and "citations" in event["chunk"]["attribution"]
            ):
                for citation in event["chunk"]["attribution"]["citations"]:
                    if (
                        "generatedResponsePart" in citation
                        and "textResponsePart" in citation["generatedResponsePart"]
                    ):
                        text_part = citation["generatedResponsePart"][
                            "textResponsePart"
                        ]["text"]
                        logger.info("Detailed response part:", text_part)
                    source_file_list = []
                    if "retrievedReferences" in citation:
                        for reference in citation["retrievedReferences"]:
                            if (
                                "content" in reference
                                and "text" in reference["content"]
                            ):
                                reference_text = reference["content"]["text"]
                                logger.info("Reference text:", reference_text)
                            if "location" in reference:
                                source_file = reference["location"]["s3Location"]["uri"]
                                source_file_list.append(source_file)
                    logger.info(f"source_file_list: {source_file_list}")

    for t in trace_list:
        if "orchestrationTrace" in t["trace"].keys():
            if "observation" in t["trace"]["orchestrationTrace"].keys():
                obs = t["trace"]["orchestrationTrace"]["observation"]
                if obs["type"] == "ACTION_GROUP":
                    sql_query_from_llm = extract_sql_query(
                        obs["actionGroupInvocationOutput"]["text"]
                    )
                    source_file_list = sql_query_from_llm

    return chunk_text, reference_text, source_file_list


def extract_sql_query(input_string):
    """
    Extracts the SQL query from a given input string.

    This function takes an input string, searches for a SQL query in it, and returns the extracted query. It
    assumes the SQL query is the first string that starts with "SELECT" and ends with a non-SQL keyword.


    example input: "\n Source: SELECT instance_type, price_per_hour \nFROM training_price\nWHERE instance_type = 'ml.m5.xlarge'\n Returned information: According to the latest information, the ml.m5.xlarge instance type costs '$0.23' per hour for training.\n\n"

    Parameters:
    - input_string (str): The input string to search for a SQL query.

    Returns:
    - str: The extracted SQL query, or None if no SQL query is found.
    """

    pattern = r"(SELECT.*?)(?=\n\s*(?:Returned information|$))"

    # Search for the pattern in the input string using DOTALL flag to match across multiple lines
    match = re.search(pattern, input_string, re.DOTALL | re.IGNORECASE)

    # If a match is found, return the matched string, otherwise return None
    if match:
        return match.group(
            1
        ).strip()  # Use strip() to remove leading/trailing whitespace
    else:
        return None


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    """
    Lambda handler to answer user's question
    """
    logger.info("Event:")
    logger.info(json.dumps(event))

    body = event["body"]
    query = body["query"]
    session_id = body["session_id"]

    
    try:
        streaming_response = invoke_agent(query, session_id)
        logger.info(f"streaming_response: {streaming_response}")
        res = get_agent_response(streaming_response)
        logger.info(f"res: {res}")

        response, _, source_file_list = res

        logger.info(f"response: {response}")
        logger.info(f"source_file_list: {source_file_list}")

        if isinstance(source_file_list, list):
            reference_str = "\n".join(source_file_list)
        else:
            reference_str = source_file_list

        logger.info(f"reference_str: {reference_str}")
    except Exception as e:
        logger.error(f"Error: {e}")
        response = f"Error getting response {e}"
        reference_str = "Error getting reference"

    output = {"answer": response, "source": reference_str}

    return output
