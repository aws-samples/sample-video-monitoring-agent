# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from connections import Connections
import time

logger = Connections.logger


def wait_for_state(
    check_fn,
    resource_identifier,
    expected_state,
    waiting_states,
    *args,
    min_interval=5,
    max_interval=60,
    max_attempts=10,
    **kwargs,
):
    """
    Generic helper that polls a state until the operation is completed or an unexpected state is encountered.

    Args:
        check_fn (callable): A function that returns a tuple (is_completed, current_state).
        resource_identifier (str): A string identifier for the resource (for logging).
        waiting_states (list): States that indicate the process is still in progress.
        max_retries (int): Maximum number of retry attempts.
        backoff_interval (int): Initial backoff interval in seconds.
        max_backoff (int): Maximum backoff interval in seconds.
        **kwargs: Additional keyword arguments passed to check_fn.

    Returns:
        bool: True if the operation completed successfully, False otherwise.
    """
    backoff_interval = min_interval
    for attempt in range(max_attempts):
        state = check_fn(*args, **kwargs)
        if state == expected_state:
            logger.info(
                f"The operation for {resource_identifier} completed successfully with state: {state}"
            )
            return state
        elif state in waiting_states:
            logger.info(
                f"The operation for {resource_identifier} is currently in state: {state}. Waiting for {expected_state}... (attempt {attempt+1}/{max_attempts})"
            )
            time.sleep(backoff_interval)
            backoff_interval = min(max_interval, backoff_interval * 2)
        else:
            logger.error(f"Unexpected state for {resource_identifier}: {state}")
            raise Exception("Unexpected state encountered")
    logger.warning(f"Maximum attempts reached for {resource_identifier}")
    raise Exception(f"Maximum attempts reached for {resource_identifier}")
