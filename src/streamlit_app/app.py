# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import streamlit as st
import boto3
from domain import Config, IS_CONFIG, CONFIG
from utils import show_footer, subscribe_to_sns
from connections import Connections

logger = Connections.logger


def submit_information():
    """Handle form submission and setup resources"""
    # Check if any configuration needs to be done
    has_monitoring = bool(st.session_state.monitoring_instructions)
    has_l1_alerts = bool(st.session_state.l1_email or st.session_state.l1_phone)
    has_l2_alerts = bool(st.session_state.l2_email or st.session_state.l2_phone)

    # Only get stack outputs if we need them
    if has_monitoring or has_l1_alerts or has_l2_alerts:
        try:
            # Get stack outputs
            outputs = Connections.stack_outputs

            # Handle SNS subscriptions
            if has_l1_alerts:
                soft_alert_topic = outputs.get("SoftAlertTopic")
                subscribe_to_sns(
                    logger,
                    Connections.sns_client,
                    soft_alert_topic,
                    email=st.session_state.l1_email,
                    phone=st.session_state.l1_phone,
                )

            if has_l2_alerts:
                high_alert_topic = outputs.get("HighAlertTopic")
                subscribe_to_sns(
                    logger,
                    Connections.sns_client,
                    high_alert_topic,
                    email=st.session_state.l2_email,
                    phone=st.session_state.l2_phone,
                )

        except Exception as e:
            logger.error("setup error", e)
            st.error(f"Error during setup: {str(e)}")


def handle_form_submission():
    """Handle form submission and setup resources"""
    # Save state first
    save_state()
    submit_information()


st.session_state.setdefault("config", Config(None, None, None, None, None, None))
st.session_state.setdefault(IS_CONFIG, False)


def save_state():
    st.session_state[CONFIG] = Config(
        st.session_state.stream_url,
        st.session_state.monitoring_instructions,
        st.session_state.l1_email,
        st.session_state.l1_phone,
        st.session_state.l2_email,
        st.session_state.l2_phone,
    )
    st.session_state[IS_CONFIG] = True
    logger.info(st.session_state[CONFIG])


def configuration_form(disabled):
    with st.form("video_stream_config", enter_to_submit=False):
        st.markdown("### Video stream configuration (blank for Agent chat only)")
        config: Config = st.session_state[CONFIG]
        st.text_input(
            "Video stream url or file absolute path",
            key="stream_url",
            value=config.stream_url,
            disabled=disabled,
        )
        st.markdown("### Additional Monitoring Instructions (optional)")
        st.text_area(
            "Additional instructions - basic surveillance and reporting instructions provided by default.",
            key="monitoring_instructions",
            value=config.monitoring_instructions,
            disabled=disabled,
        )

        # Wrap alert configuration in expander
        with st.expander("Alert configuration (optional)", expanded=False):
            with st.container(border=True):
                st.markdown("Level 0: All events logged for review")
            with st.container(border=True):
                st.markdown("Alert Level 1 (Potential issues)")
                st.text_input(
                    ":material/email: Email",
                    key="l1_email",
                    value=config.l1_email,
                    disabled=disabled,
                )
                st.text_input(
                    ":material/call: Phone",
                    key="l1_phone",
                    value=config.l1_phone,
                    disabled=disabled,
                )
            with st.container(border=True):
                st.markdown("Alert Level 2 (Immediate action)")
                st.text_input(
                    ":material/email: Email",
                    key="l2_email",
                    value=config.l2_email,
                    disabled=disabled,
                )
                st.text_input(
                    ":material/call: Phone",
                    key="l2_phone",
                    value=config.l2_phone,
                    disabled=disabled,
                )

        if st.form_submit_button(
            "Start", on_click=handle_form_submission, disabled=disabled
        ):
            st.switch_page("pages/chat_video_analysis.py")


def main():
    configuration_form(IS_CONFIG in st.session_state and st.session_state[IS_CONFIG])
    show_footer()


if __name__ == "__main__":
    main()
