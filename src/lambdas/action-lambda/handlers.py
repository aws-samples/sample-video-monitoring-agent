# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import json
import logging
from typing import Dict, Any, List

from process_image import image_to_text
from connections import Connections
from build_query_engine import query_engine
from utils import get_named_parameter
import ast
from bedrock_utils import create_text_prompt, invoke_bedrock_model

logger = Connections.logger


def process_image_analysis(parameters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Handle image analysis requests"""
    file_name = get_named_parameter(parameters, "image_file_name")
    monitoring_instructions = get_named_parameter(parameters, "monitoring_instructions")
    try:
        logger.info(
            f"Downloading image from s3://{Connections.agent_bucket_name}/{file_name}"
        )
        response = Connections.s3_client.get_object(
            Bucket=Connections.agent_bucket_name, Key=file_name
        )
        detected_event_data = image_to_text(
            response["Body"].read(), response["ContentType"], monitoring_instructions
        )
        logger.info(
            f"Detected event  type: {type(detected_event_data)}, data: {detected_event_data}"
        )
        return {"source": file_name, "answer": detected_event_data}
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise


def process_alert(parameters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Handle alert notifications"""
    detected_event_data = get_named_parameter(parameters, "detected_event_data")
    event_data = json.loads(detected_event_data)

    topic_arn = (
        Connections.high_alert_topic
        if event_data["alert_level"] == 2
        else Connections.soft_alert_topic
    )

    try:
        Connections.sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps(
                {
                    "default": detected_event_data,
                    "email": f"Alert Level {event_data['alert_level']}: {event_data['brief_description']}\n\n{event_data['full_description']}",
                }
            ),
            MessageStructure="json",
        )
        logger.info(
            f"Alert level {event_data['alert_level']} notification sent successfully to {topic_arn}"
        )
        return {
            "source": "SNS Alert System",
            "answer": f"Alert level {event_data['alert_level']} notification sent successfully",
        }
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        raise


def process_log(parameters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Handle event logging to S3"""
    logger.info(f"Processing log event: {parameters}")
    detected_event_data = get_named_parameter(parameters, "detected_event_data")
    event_data = json.loads(detected_event_data)

    log_key = (
        f"{Connections.knowledgebase_destination_prefix}/{event_data['log_file_name']}"
    )

    try:
        Connections.s3_client.put_object(
            Bucket=Connections.agent_bucket_name,
            Key=log_key,
            Body=json.dumps(event_data, indent=2),
        )
        logger.info(f"Event logged to s3://{Connections.agent_bucket_name}/{log_key}")
        return {"source": log_key, "answer": f"Event logged successfully to {log_key}"}
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        raise


def process_vehicle_lookup(parameters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Handle vehicle lookup using query engine"""
    user_input = get_named_parameter(parameters, "vehicleQuestion")

    try:
        response = query_engine.query(user_input)

        return {"source": response.metadata["sql_query"], "answer": response.response}
    except Exception as e:
        logger.error(f"Error in vehicle lookup: {e}")
        raise


def _get_events_in_range(date_range: Dict[str, str]) -> List[Dict]:
    """
    Retrieve events from S3 within the specified date range.

    Args:
        date_range: Dictionary with 'start' and 'end' date strings

    Returns:
        List of events with timestamp and data
    """

    logger.info(f"Searching for events in {date_range['start']} to {date_range['end']}")

    s3_resource = Connections.s3_resource
    bucket = s3_resource.Bucket(Connections.agent_bucket_name)
    prefix = f"{Connections.knowledgebase_destination_prefix}/"
    events = []
    for obj in bucket.objects.filter(Prefix=prefix):
        try:
            key_parts = obj.key.split("/")
            if len(key_parts) < 2:
                continue

            timestamp_part = key_parts[1].split("_")[0]

            logger.info(f"Event timestamp: {timestamp_part}")

            if date_range["start"] <= timestamp_part <= date_range["end"]:
                event_obj = obj.get()
                event_data = json.loads(event_obj["Body"].read())
                events.append({"timestamp": timestamp_part, "data": event_data})
                logger.info(f"Added event with timestamp: {timestamp_part}")
        except (IndexError, ValueError) as e:
            logger.error(f"Skipping malformed key {obj.key}: {e}")
            continue

    # Sort events chronologically
    events.sort(key=lambda x: x["timestamp"])
    logger.info(f"Found {len(events)} events in the specified time range")

    return events


def process_date_search(parameters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Handle historical event searches"""
    user_question = get_named_parameter(parameters, "user_question")
    date_range = ast.literal_eval(get_named_parameter(parameters, "date_range"))

    try:

        events = _get_events_in_range(date_range)

        logger.info(f"Found {len(events)} events in the specified time range")
        if not events:
            return {
                "source": "Event Search",
                "answer": f"No events found in the specified time range.",
            }

        # Construct prompt for Bedrock
        content = f"""Here is a question about some security camera events:
                {user_question}

                Here are the relevant events from {date_range["start"]} to {date_range["end"]} in chronological order:

                {json.dumps(events, indent=2)}

                Please give a concise answer to the question based on the events provided. Answer in a well formatted event report utilizing the information from the events. Do one final check to ensure the information in the report directly answers the question. If the information is not present in the events, please explain your reasoning."""

        prompt = create_text_prompt(content=content)
        analysis = invoke_bedrock_model(prompt=prompt)

        logger.info(f"Bedrock analysis: {analysis}")

        return {"source": "Event Search and Analysis", "answer": analysis}

    except Exception as e:
        logger.error(f"Error processing date searach request: {e}")
