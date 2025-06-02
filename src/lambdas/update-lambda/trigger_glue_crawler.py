# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from connections import Connections
from utils import wait_for_state

logger = Connections.logger


def check_crawler_state(glue_client, crawler_name):
    """
    Checks the current state of the crawler.

    Args:
        glue_client: The Glue client.
        crawler_name (str): The name of the crawler.

    Returns:
        The current crawler state.
    """
    crawler_metadata = glue_client.get_crawler(Name=crawler_name)
    return crawler_metadata["Crawler"]["State"]


def trigger_glue_crawler(glue_client, crawler_name):
    """
    Triggers a Glue crawler.

    Args:
        glue_client (boto3.client): The Glue client.
        crawler_name (str): The name of the crawler to trigger.

    Returns:
        None.
    """
    # Start the Glue Crawler.
    _ = glue_client.start_crawler(Name=crawler_name)
    logger.info(f"Triggered Crawler {crawler_name}. Waiting for it to complete...")

    try:
        # Wait for the crawler to reach the "READY" state.
        final_state = wait_for_state(
            check_fn=check_crawler_state,
            resource_identifier="Trigger Glue Crawler",
            expected_state="READY",
            waiting_states=["RUNNING", "STOPPING"],
            glue_client=glue_client,
            crawler_name=crawler_name,
        )
        logger.info(
            f"Crawler {crawler_name} completed successfully with state {final_state}."
        )
    except Exception as e:
        logger.error(f"Crawler {crawler_name} failed with error: {e}")
        raise
