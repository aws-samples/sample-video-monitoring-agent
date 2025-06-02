# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from typing import Dict, Any, List


def get_named_parameter(
    parameters: List[Dict[str, Any]], name: str, default: Any = "NoValueFound"
) -> Any:
    """Extract a named parameter from the parameters list"""
    return next(
        (item for item in parameters if item["name"] == name), {"value": default}
    )["value"]


def format_response(
    prediction: Dict[str, Any], output: Dict[str, str], status_code: int
) -> Dict[str, Any]:
    """Format the Lambda response for Bedrock Agent"""
    # Format the content as expected by the agent
    body = f"""
    Source: {output["source"]}
    Returned information: {output["answer"]}
    """

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": prediction["actionGroup"],
            "apiPath": prediction["apiPath"],
            "httpMethod": prediction["httpMethod"],
            "httpStatusCode": status_code,
            "responseBody": {"application/json": {"body": body}},
        },
    }
