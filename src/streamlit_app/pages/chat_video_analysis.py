# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import multiprocessing
from datetime import datetime
from datetime import timedelta
from time import sleep

import streamlit as st

from connections import Connections
from domain import Config, CONFIG
from response_handler import ResponseHandler
from shared.logic import VideoStreamSource, FrameProcessorChain, VideoStreamProcessor
from shared.processors import (
    SimpleMotionDetection,
    FrameSampling,
    GridAggregator,
    S3Storage,
    LambdaProcessor,
)
from utils import show_footer, clear_input, show_empty_container

logger = Connections.logger

TARGET_S3_BUCKET = Connections.stack_outputs["AssetsBucket"]
S3_PREFIX = Connections.s3_prefix


@st.fragment
def video_stream_section():
    config: Config = st.session_state[CONFIG]
    if not config.stream_url:
        st.info("No video stream provided - chat only mode activated")
        return

    # Create a permanent container for the video
    if "video_container" not in st.session_state:
        st.session_state.video_container = st.empty()

    if "video_initialized" not in st.session_state:
        logger.info("First time initializing video")

        # Display video in the permanent container
        with st.session_state.video_container:
            if config.stream_url == "0":
                config.stream_url = 0
                st.camera_input("Camera capture")
            else:
                # Display video
                st.video(config.stream_url, autoplay=True)

        # Create status containers
        st.session_state.status_container = st.empty()
        st.session_state.events_container = st.container()

        # Initialize processing components
        ctx = multiprocessing.get_context("spawn")
        source = VideoStreamSource(ctx, config.stream_url, queue_size=250)
        chain = FrameProcessorChain(
            [
                SimpleMotionDetection(motion_threshold=10_000, frame_skip_size=1),
                FrameSampling(
                    timedelta(milliseconds=250), threshold_time=timedelta(seconds=2)
                ),
                GridAggregator(shape=(13, 3)),
            ]
        )
        processor = VideoStreamProcessor(ctx, source.output, chain, 1)
        storage_chain = FrameProcessorChain(
            [
                S3Storage(
                    bucket_name=TARGET_S3_BUCKET,
                    prefix=S3_PREFIX,
                    s3_client_provider=Connections.s3_client_provider,
                ),
                LambdaProcessor(
                    response_handler=ResponseHandler(Connections.lambda_function_name, Connections.lambda_client_provider),
                    monitoring_instructions=config.monitoring_instructions,
                ),
            ]
        )
        sink = VideoStreamProcessor(ctx, processor.output, storage_chain, 8)
        # Store in session state
        st.session_state.source = source
        st.session_state.processor = processor
        st.session_state.sink = sink

        # Define the processing function
        def process_video():
            try:
                sink.start()
                processor.start()
                source.start()

                while source.running:
                    sleep(0.1)

                # Cleanup when done
                source.stop()
                processor.stop()
                sink.stop()
                st.session_state.processing_complete = True
            except Exception as e:
                st.session_state.processing_error = str(e)
                logger.error(f"Error in video processing: {e}")

        # Start processing in background thread
        import threading

        processing_thread = threading.Thread(target=process_video, daemon=True)
        # button to change source.running to false
        st.button("Stop", on_click=lambda: source.stop())
        processing_thread.start()

        st.session_state.video_initialized = True
        st.session_state.processing_complete = False
    else:
        # Rerender the video in the same container on page refreshes
        with st.session_state.video_container:
            if config.stream_url == 0:
                st.camera_input("Camera capture")
            else:
                # Display video
                st.video(config.stream_url, autoplay=True)

    # Status updates (in main thread)
    with st.session_state.status_container:
        if not st.session_state.get("processing_complete", False):
            st.info(
                f"Processing video stream... Frame: {st.session_state.get('current_frame', 0)}"
            )
            if error := st.session_state.get("processing_error"):
                st.error(f"Processing error: {error}")
        else:
            st.success("Video processing complete!")


def header():
    """
    App Header setting
    """
    # --- Set up the page ---
    st.set_page_config(
        page_title="Bedrock Video Monitoring Agent & Chatbot",
        page_icon=":video_camera:",
        layout="centered",
    )

    # Creating two columns, logo on the left and title on the right
    col1, col2 = st.columns(
        [1, 3]
    )  # The ratio between columns can be adjusted as needed

    with col1:
        st.image(
            "../../assets/icons/camera.jpg",
            width=150,
        )

    with col2:
        st.markdown("# Video Monitoring Agent")

    st.write("#### Monitor a video stream and ask about captured events.")
    st.write("-----")


def initialization():
    """
    Initialize sesstion_state variablesß
    """
    # --- Initialize session_state ---
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(datetime.now()).replace(" ", "_")
        st.session_state.questions = []
        st.session_state.answers = []

    if "temp" not in st.session_state:
        st.session_state.temp = ""

    # Initialize cache in session state
    if "cache" not in st.session_state:
        st.session_state.cache = {}


def show_message():
    """
    Show user question and answers
    """

    # --- Start the session when there is user input ---
    user_input = st.text_input("# **Question:** 👇", "", key="input")

    logger.info(f"user_input: {user_input}")
    # Start a new conversation
    new_conversation = st.button("New Conversation", key="clear", on_click=clear_input)
    if new_conversation:
        st.session_state.session_id = str(datetime.now()).replace(" ", "_")
        st.session_state.user_input = ""

    if user_input:
        session_id = st.session_state.session_id
        with st.spinner("Gathering info ..."):
            vertical_space = show_empty_container()
            vertical_space.empty()
            response_output = "No response"
            try:
                response_output = ResponseHandler(Connections.lambda_function_name,
                                                  Connections.lambda_client_provider).get_response(user_input,
                                                                                                   session_id)
                logger.info(f"response_output: {response_output}")
                st.write("-------")
                source_title = ""
                # check if response_output["source"] is a string
                if response_output["source"] and isinstance(
                    response_output["source"], str
                ):
                    source_title = (
                        "\n\n **Source**:" + "\n\n" + response_output["source"]
                    )
                answer = "**Answer**: \n\n" + response_output["answer"]
            except Exception as e:
                answer = f"Error in get_response: {e}. Response: {response_output}"
                logger.error(answer)

            st.session_state.questions.append(user_input)
            st.session_state.answers.append(answer + source_title)

    if st.session_state["answers"]:
        for i in range(len(st.session_state["answers"]) - 1, -1, -1):
            with st.chat_message(
                name="human",
                avatar="../../assets/icons/avatar.png",
            ):
                st.markdown(st.session_state["questions"][i])

            with st.chat_message(
                name="ai",
                avatar="../../assets/icons/bot.png",
            ):
                st.markdown(st.session_state["answers"][i])


def main():
    header()
    if not "is_config" in st.session_state or not st.session_state["is_config"]:
        st.switch_page("app.py")
    video_stream_section()

    initialization()
    show_message()
    show_footer()


if __name__ == "__main__":
    main()
