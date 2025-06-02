# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os, pathlib, tempfile
TMP_DIR = tempfile.gettempdir()  

# Writable cache locations
os.environ.setdefault("NLTK_DATA", TMP_DIR)
os.environ.setdefault("TIKTOKEN_CACHE_DIR", f"{TMP_DIR}/tiktoken_cache")

# Create the cache dir once per container
pathlib.Path(os.environ["TIKTOKEN_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
from typing_extensions import Annotated
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.utilities.typing import LambdaContext
from handlers import (
    process_image_analysis,
    process_alert,
    process_log,
    process_date_search,
    process_vehicle_lookup,
)
from connections import Connections

tracer = Tracer()
logger = Connections.logger
app = BedrockAgentResolver()


@app.get(
    "/analyze_grid",
    description="Use this endpoint to analyze an image grid when motion is detected. Provide the image filename for analysis. Only use this when provided an image file name, do not make up your own.",
)
@tracer.capture_method
def handle_analyze_grid(
    image_file_name: Annotated[
        str, Query(description="The name of the image file to analyze.")
    ],
    monitoring_instructions: Annotated[
        str,
        Query(
            description="Additional monitoring instructions provided with the request. If none avilalbe, provide 'None'."
        ),
    ],
) -> dict:
    return process_image_analysis(app.current_event["parameters"])


@app.get(
    "/log",
    description="Log a detected event by passing the relevant JSON string. Used to record events in a storage/log file.",
)
@tracer.capture_method
def handle_log(
    detected_event_data: Annotated[
        str,
        Query(
            description='JSON string containing event data to log. Example: {"alert_level":2,"reason":"Package theft","log_file_name":"event.json","brief_description":"Brief desc","full_description":"Full desc"}'
        ),
    ]
) -> dict:
    return process_log(app.current_event["parameters"])


@app.get(
    "/alert",
    description="Send an alert based on a detected event by passing in the relevant JSON string. Typically used to notify administrators or systems",
)
@tracer.capture_method
def handle_alert(
    detected_event_data: Annotated[
        str,
        Query(
            description='JSON string containing event data to log. Example: {"alert_level":2,"reason":"Package theft","log_file_name":"event.json","brief_description":"Brief desc","full_description":"Full desc"}'
        ),
    ]
) -> dict:
    return process_alert(app.current_event["parameters"])


@app.get(
    "/search_dates",
    description="Answer a question about events in a given date range only when a date range is referenced in the question. You can use this to recall detailed information about all events in a date rane, and you can use this to answer any question about past events in a given date range. If a period such as 'last week' or 'last month' is provided, use the current time to convert this to a the date range. The date range format is YYYYMMDD-HHMMSS.",
)
@tracer.capture_method
def handle_search_dates(
    user_question: Annotated[
        str, Query(description="The question or query about historical events.")
    ],
    date_range: Annotated[
        str,
        Query(
            description='JSON string with start and end timestamps,on the following format {"start":"YYYYMMDD-HHMMSS","end":"YYYYMMDD-HHMMSS"}'
        ),
    ],
) -> dict:
    return process_date_search(app.current_event["parameters"])


@app.get(
    "/lookup_vehicle",
    description="Converts a user question about vehicles into a SQL query and queries the vehicle table. Use this for any attempt to find known vehicles or vehicle information in a structured database. Never guess or recall from memory. If you have image data or descriptions, use them as context to form the SQL query.",
)
@tracer.capture_method
def handle_vehicle_lookup(
    vehicleQuestion: Annotated[
        str, Query(description="A question in natural language about known vehicles.")
    ]
) -> dict:
    return process_vehicle_lookup(app.current_event["parameters"])


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def get_response(event: dict, context: LambdaContext):
    try:
        response = app.resolve(event, context)
    except Exception as e:
        response = {
            "statusCode": 500,
            "body": {
                "error": str(e),
                "message": "An error occurred while processing the request.",
            },
        }
    logger.info(f"Response: {response}")
    return response


if __name__ == "__main__":
    print(app.get_openapi_json_schema())
