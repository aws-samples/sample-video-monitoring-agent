import json
from dataclasses import asdict
from datetime import datetime, timezone

from aws_lambda_powertools import Logger

from domain import Query, Payload


class ResponseHandler:
    def __init__(self,lambda_function_name, lambda_client_provider):
        self._lambda_function_name = lambda_function_name
        self._lambda_client_provider= lambda_client_provider

    def get_response(self, user_input, session_id, invocation_type="RequestResponse"):
        """
        Get response from genai Lambda
        """
        logger = Logger()
        logger.info(f"session id: {session_id}")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        query_text = f"Timestamp: {timestamp}. \ninput:{user_input}\nRespond with the final answer to the input:"
        logger.info(f"query_text: {query_text}")
        query = Query(query=query_text, session_id=session_id)
        payload = Payload(body=query)
        payload_dict = asdict(payload)

        logger.info(f"lambda_function_arn: {self._lambda_function_name}")
        logger.info(f"payload: {payload_dict}")

        response = self._lambda_client_provider().invoke(
            FunctionName=self._lambda_function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload_dict),
        )
        response_body = response["Payload"].read().decode("utf-8")
        logger.info(f"response_body: {response_body}")

        if invocation_type == "Event":
            response_output = {"answer": "Invoke agent triggered.", "source": ""}
        else:
            response_output = json.loads(response_body)

        logger.info(f"response_output from genai lambda: {response_output}")
        return response_output