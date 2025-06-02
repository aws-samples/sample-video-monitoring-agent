# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import streamlit as st
from botocore.exceptions import ClientError


def get_stack_outputs(stack_name, cfn_client):
    """Get CloudFormation stack outputs"""
    try:
        response = cfn_client.describe_stacks(StackName=stack_name)
        outputs = {}
        for output in response["Stacks"][0]["Outputs"]:
            outputs[output["OutputKey"]] = output["OutputValue"]
        return outputs
    except ClientError as e:
        st.error(f"Error getting stack outputs: {str(e)}")
        return {}


def subscribe_to_sns(logger, sns_client, topic_arn, email=None, phone=None):
    """Subscribe email or phone to SNS topic"""
    try:
        if email:
            sns_client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)
            logger.info(f"Subscription email sent to {email}")

        if phone:
            sns_client.subscribe(TopicArn=topic_arn, Protocol="sms", Endpoint=phone)
            logger.info(f"Subscription SMS sent to {phone}")
    except ClientError as e:
        logger.info(f"Error subscribing to SNS: {str(e)}")


def clear_input():
    """
    Clear input when clicking `Clear conversation`.
    """
    # st.session_state.session_id = ""
    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state["temp"] = st.session_state["input"]
    st.session_state["input"] = ""


def show_empty_container(height: int = 100) -> st.container:  # <----
    """
    Display empty container to hide UI elements below while thinking

    Parameters
    ----------
    height : int
        Height of the container (number of lines)

    Returns
    -------
    st.container
        Container with large vertical space
    """
    empty_placeholder = st.empty()
    with empty_placeholder.container():
        st.markdown("<br>" * height, unsafe_allow_html=True)
    return empty_placeholder


def show_footer() -> None:
    """
    Show footer with AWS copyright
    """

    st.markdown("---")
    st.markdown(
        "<div style='text-align: right'> © 2025 Amazon Web Services </div>",
        unsafe_allow_html=True,
    )
