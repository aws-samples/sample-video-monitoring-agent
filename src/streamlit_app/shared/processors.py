# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import cv2
from numpy import ndarray, zeros, uint8

from connections import Connections
from shared.logic import FrameProcessor, Frame

logger = Connections.logger

MOTION_DETECTED = "motion_detected"
GRID_SHAPE = "grid_shape"


class LocalStorage(FrameProcessor):
    def process(self, frame: Frame) -> Frame:
        cv2.imwrite(
            f"{int(frame.index)}-img.jpg", frame.buffer, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        logger.info(
            f"Saved frame #{int(frame.index)}, timestamp: {frame.timestamp}, fps: {frame.fps}"
        )
        return frame


class S3Storage(FrameProcessor):
    def __init__(self, bucket_name: str, prefix: str, s3_client_provider):
        # This is a workaround for the pickle multiprocessing issue
        self.s3_client_provider = s3_client_provider
        self.bucket_name = bucket_name
        self.prefix = prefix

    def process(self, frame: Frame) -> Optional[Frame]:
        try:
            success, encoded_img = cv2.imencode(
                ".jpg", frame.buffer, [cv2.IMWRITE_JPEG_QUALITY, 90]
            )
            if not success:
                raise RuntimeError("Failed to encode image")
            key = f"{self.prefix}/{int(frame.index)}.jpg"
            self.s3_client_provider().put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=encoded_img.tobytes(),
                ContentType="image/jpeg",
                Metadata={
                    "frame_index": str(int(frame.index)),
                    "timestamp": str(frame.timestamp),
                    "fps": str(frame.fps),
                },
            )
            logger.info(
                f"\n\n ** Saved frame #{int(frame.index)}, timestamp: {frame.timestamp}, fps: {frame.fps} to s3://{self.bucket_name}/{key} **\n\n"
            )
            frame.metadata["s3_key"] = key
        except Exception as e:
            logger.error(f"Error saving frame to S3: {str(e)}")
            raise e

        return frame


class LambdaProcessor(FrameProcessor):
    def __init__(self, response_handler, monitoring_instructions):
        logger.info("LambdaProcessor init")
        self.response_handler = response_handler
        self.monitoring_instructions = monitoring_instructions
        self.session_id = "motion_" + str(uuid.uuid4())

    def process(self, frame: Frame) -> Frame:
        try:
            if "s3_key" not in frame.metadata:
                logger.info("No s3_key in metadata, skipping Lambda processing")
                return frame
            logger.debug(f"Invoking agent")

            detected_input: str = self._prepare_detected_input(frame)

            response = self.response_handler.get_response(
                detected_input, self.session_id, invocation_type="Event"
            )
            logger.debug(f"Agent response: {response}")
            frame.metadata.update(
                {
                    "agent_response": response,
                }
            )

        except Exception as e:
            logger.error(f"Error in Lambda processing: {str(e)}")

        return frame

    def _prepare_detected_input(self, frame: Frame) -> str:
        return (
            f"Motion detected - the following image grid was captured: {frame.metadata['s3_key']}. "
            f"<additional_monitoring_instructions>{self.monitoring_instructions}</additional_monitoring_instructions>"
        )


class SimpleMotionDetection(FrameProcessor):
    def __init__(
        self, thresh_binary=25, motion_threshold: int = 30_000, frame_skip_size: int = 3
    ):
        self._thresh_binary = thresh_binary
        self._motion_threshold = motion_threshold
        self._prev_grays: deque[ndarray] = deque(maxlen=frame_skip_size)
        self._frame_skip_size = frame_skip_size

    def process(self, frame: Frame) -> Optional[Frame]:
        if self._detect_motion(frame):
            frame.metadata = {**frame.metadata, MOTION_DETECTED: True}

        return frame

    def _detect_motion(self, frame: Frame) -> bool:
        current_gray = cv2.cvtColor(frame.buffer, cv2.COLOR_BGR2GRAY)
        if len(self._prev_grays) >= self._frame_skip_size:
            prev_gray = self._prev_grays.popleft()
            diff = cv2.absdiff(prev_gray, current_gray)
            _, thresh = cv2.threshold(diff, self._thresh_binary, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh)
            result = changed_pixels > self._motion_threshold
        else:
            result = False

        self._prev_grays.append(current_gray)

        return result


class MotionSelecting(FrameProcessor):
    def process(self, frame: Frame) -> Optional[Frame]:
        if frame.metadata.get(MOTION_DETECTED, False):
            return frame
        else:
            return None


class FrameSampling(FrameProcessor):
    def __init__(self, sampling: timedelta, threshold_time: timedelta):
        """
        We assume Frame.timestamp is in milliseconds
        :param sampling: time between consecutive frames to capture
        """
        self._sampling = sampling.total_seconds() * 1000
        self._last_frame = None
        self._threshold_time = threshold_time

    def process(self, frame: Frame) -> Optional[Frame]:
        logger.info(f"FrameSampling called, frame #{int(frame.index)}")
        if frame.metadata.get(MOTION_DETECTED):
            if (
                self._last_frame is None
                or frame.timestamp - self._last_frame >= self._sampling
            ):
                self._last_frame = frame.timestamp
                logger.info(
                    f"Motion detected in frame #{int(frame.index)}, timestamp: {frame.timestamp}, fps: {frame.fps}"
                )
                return frame

        # No motion detected in sample, checking for threshold time
        if (
            self._last_frame
            and (frame.timestamp - self._last_frame)
            > self._threshold_time.total_seconds() * 1000
        ):
            logger.debug(
                f"Threshold time without motion reached frame #{int(frame.index)}"
            )
            logger.debug(
                f"Time since last motion: {(frame.timestamp - self._last_frame)} > {self._threshold_time.total_seconds() * 1000}"
            )
            frame.metadata["motion_end"] = True
            return frame


class GridAggregator(FrameProcessor):

    def __init__(
        self,
        shape: tuple[int, int],
        border_color: tuple[int, int, int] = (0, 0, 0),
        border_thickness: int = 10,
        text_color: tuple[int, int, int] = (255, 255, 255),
        font: int = cv2.FONT_HERSHEY_SIMPLEX,
        font_scale: int = 1,
        font_thickness: int = 1,
    ):
        self._index = 0
        self._shape: tuple[int, int] = shape
        self._rows, self._columns = shape
        self._frame_buffer_size = self._rows * self._columns
        self._frame_buffer: deque[Frame] = deque(maxlen=self._frame_buffer_size)
        self._last_frame: Optional[datetime] = None
        self._text_color = text_color
        self._border_color = border_color
        self._font = font
        self._font_scale = font_scale
        self._font_thickness = font_thickness
        self._border_thickness = border_thickness

    def process(self, frame: Frame) -> Optional[Frame]:
        # time check: clear deque if it was not used for a threshold time
        if frame.metadata.get("motion_end"):

            # only dump to grid if enough frames are captured
            if len(self._frame_buffer) < 3:
                self._frame_buffer.clear()

            else:
                logger.info(f"** Motion end ** buffer size: {len(self._frame_buffer)}")
                rows = (len(self._frame_buffer) // self._columns) + 1
                grid = self._create_grid(rows, self._columns)
                grid_frame = Frame(
                    grid,
                    datetime.now().timestamp(),
                    self._index,
                    0,
                    {GRID_SHAPE: (self._rows, self._columns)},
                )
                self._frame_buffer.clear()
                self._index += 1
                return grid_frame
        self._last_frame = datetime.now()

        # size check
        self._frame_buffer.append(frame)
        if len(self._frame_buffer) < self._frame_buffer_size:
            return None

        grid = self._create_grid(self._rows, self._columns)
        self._frame_buffer.clear()

        # TODO: change fps to some calculated value when metrics are added
        grid_frame = Frame(
            grid, datetime.now().timestamp(), self._index, 0, {GRID_SHAPE: self._shape}
        )
        self._index += 1
        return grid_frame

    def _create_grid(self, rows, columns):
        logger.info(f"Create grid called, buffer size = {len(self._frame_buffer)}")
        images = []
        for frame in self._frame_buffer:
            description = f"#{int(frame.index)}, timestamp: {frame.timestamp:.0f}, fps: {frame.fps}"
            img = self._get_image_with_border(frame.buffer, description)

            h, w = img.shape[:2]
            scale = min(600 / h, 900 / w)
            if scale < 1:
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            images.append(img)

        h, w = img.shape[:2]

        while len(images) < rows * columns:
            empty_frame = zeros((h, w, 3), dtype=uint8)

            if empty_frame.shape != img.shape:
                raise ValueError(
                    f"Unexpected shape mismatch: {empty_frame.shape} != {img.shape}"
                )

            images.append(empty_frame)

        rows_list = []
        for i in range(0, len(images), self._columns):
            row = cv2.hconcat(images[i : i + self._columns])
            rows_list.append(row)

        # Concatenate rows vertically
        grid = cv2.vconcat(rows_list)
        return grid

    # TODO: we assume here images will be the same size and description will be the same size. Also text width is less than image width
    def _get_image_with_border(self, image, description):
        (text_width, text_height), _ = cv2.getTextSize(
            description, self._font, self._font_scale, self._font_thickness
        )
        height, width = image.shape[:2]
        top = left = right = self._border_thickness
        bottom = self._border_thickness + text_height
        text_x = (width - text_width) // 2
        text_y = height + top + (bottom + text_height) // 2

        img = cv2.copyMakeBorder(
            image,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=self._border_color,
        )
        cv2.putText(
            img,
            description,
            (text_x, text_y),
            self._font,
            self._font_scale,
            self._text_color,
            self._font_thickness,
        )
        return img
