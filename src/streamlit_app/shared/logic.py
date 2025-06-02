# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import multiprocessing as mp
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from multiprocessing import JoinableQueue
from time import sleep
from typing import Optional
from datetime import datetime
import cv2
from numpy import ndarray
from connections import Connections

logger = Connections.logger


@dataclass
class Frame:
    buffer: ndarray
    timestamp: float
    index: float
    fps: float
    metadata: dict = field(default_factory=dict)


# TODO: add automatic metrics like fps etc
class FrameProcessor(ABC):

    @abstractmethod
    def process(self, frame: Frame) -> Optional[Frame]: ...


class FrameProcessorChain(FrameProcessor):
    def __init__(self, chain: list[FrameProcessor]):
        self._chain = chain

    def process(self, frame: Frame) -> Optional[Frame]:
        current = frame
        for processor in self._chain:
            if current:
                current = processor.process(current)
        return current


class VideoStreamSource:

    def __init__(self, ctx, video_source, queue_size=32):
        self._video_source = video_source
        self._output = ctx.JoinableQueue(maxsize=queue_size)
        self._running = ctx.Value("b", False)
        self._producer: ctx.Process = ctx.Process(
            target=self._capture_frames,
            args=(self._video_source, self._output, self._running),
            daemon=True,
        )

    def start(self):
        if self._running.value:
            return
        self._running.value = True
        self._producer.start()

    def stop(self):
        logger.info(f"** Motion end ** buffer size: {len(self._frame_buffer)}")
        if not self._running.value:
            return
        self._running.value = False
        self._producer.join(timeout=1.0)
        if self._producer.is_alive():
            self._producer.terminate()

        while not self._output.empty():
            try:
                self._output.get_nowait()
            except:
                pass
        self._output.close()
        self._output.join_thread()
        logger.info("Video source stopped")

    @property
    def output(self):
        return self._output

    @property
    def running(self):
        return self._running.value

    @staticmethod
    def get_frame(stream: cv2.VideoCapture):
        # https://docs.opencv.org/4.10.0/d4/d15/group__videoio__flags__base.html#gaeb8dd9c89c10a5c63c139bf7c4f5704d
        fps = stream.get(cv2.CAP_PROP_FPS)
        timestamp = stream.get(cv2.CAP_PROP_POS_MSEC)
        if not timestamp:
            timestamp = datetime.now().timestamp() * 1000
        index = stream.get(cv2.CAP_PROP_POS_FRAMES)
        success, frame = stream.read()

        return success, Frame(frame, timestamp, index, fps)

    @staticmethod
    def _capture_frames(video_source, frame_queue, running):
        # https://docs.opencv.org/4.10.0/d8/dfe/classcv_1_1VideoCapture.html
        stream = cv2.VideoCapture(video_source)

        while running.value:
            if not frame_queue.full():
                success, frame = VideoStreamSource.get_frame(stream)
                if not success:
                    running.value = False
                    break
                frame_queue.put(frame)
            else:
                sleep(0.1)

        stream.release()


class VideoStreamProcessor:

    def __init__(
        self,
        ctx,
        input_queue: JoinableQueue,
        frame_processor: FrameProcessor,
        num_workers=None,
    ):
        self._ctx = ctx
        self._frame_processor = frame_processor
        self._input = input_queue
        self._output = ctx.JoinableQueue()
        self._running = ctx.Value("b", False)
        self._num_workers = num_workers or mp.cpu_count()
        self._processes = [
            self._ctx.Process(
                target=self._process_frames,
                args=(self._input, self._output, self._running, self._frame_processor),
                daemon=True,
            )
            for _ in range(self._num_workers)
        ]

    def start(self):
        if self._running.value:
            return

        self._running.value = True
        for process in self._processes:
            process.start()

    def stop(self):
        logger.info("Stopping video processor")
        if not self._running.value:
            return

        self._running.value = False

        for process in self._processes:
            process.join(timeout=1.0)
            if process.is_alive():
                process.terminate()

        while not self._output.empty():
            try:
                self._output.get_nowait()
            except:
                pass
        self._output.close()
        self._output.join_thread()
        logger.info("Video processor stopped")

    @property
    def output(self):
        return self._output

    @property
    def running(self):
        return self._running.value

    @staticmethod
    def _process_frames(
        frame_queue, result_queue, running, frame_processor: FrameProcessor
    ):
        while running.value:
            try:
                if not frame_queue.empty():
                    frame = frame_queue.get()
                    processed_frame = frame_processor.process(frame)
                    if processed_frame is not None:
                        result_queue.put(processed_frame)
                else:
                    sleep(0.1)
            except Exception as e:
                logger.error(f"Error in processing process: {e}")
                raise e
