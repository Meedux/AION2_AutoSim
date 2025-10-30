"""Detection controller: ties capture, workflow client, and overlay together."""
import threading
import time
from typing import Callable
from loguru import logger
from capture import CaptureWorker
from roboflow_client import WorkflowClient
from utils import jpeg_bytes_from_bgr


class DetectionController:
    def __init__(self, hwnd: int, workspace_name: str, workflow_id: str, api_key: str, overlay_update: Callable, log_fn: Callable, fps: int = 10):
        """overlay_update(detections, (w,h)) will be called on each new result or tick.
        log_fn(text) will be called to output logs to UI.
        """
        self.hwnd = hwnd
        self.workspace_name = workspace_name
        self.workflow_id = workflow_id
        self.api_key = api_key
        self.overlay_update = overlay_update
        self.log = log_fn
        self.fps = fps

        self.capture = CaptureWorker(hwnd=hwnd, target_fps=max(5, fps*2), resize_max=960)
        self.client = WorkflowClient(api_key=api_key)

        self._worker = threading.Thread(target=self._run, daemon=True)
        self._running = threading.Event()

        # last known detections and frame size
        self._detections = []
        self._frame_size = (0, 0)

    def start(self):
        self.log("Starting capture and detection")
        self.capture.start_capture()
        self._running.set()
        if not self._worker.is_alive():
            self._worker.start()

    def stop(self):
        self.log("Stopping detection")
        self._running.clear()
        self.capture.stop_capture()

    def _run(self):
        interval = 1.0 / max(1, self.fps)
        while self._running.is_set():
            frame = self.capture.get_latest_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            h, w = frame.shape[:2]
            self._frame_size = (w, h)
            try:
                # encode to jpeg bytes
                jbytes = jpeg_bytes_from_bgr(frame, quality=70)
                resp = self.client.run_workflow_on_bytes(self.workspace_name, self.workflow_id, jbytes, use_cache=True)
                preds = self.client.parse_predictions(resp)
                # convert center-based to top-left if needed
                conv = []
                for p in preds:
                    try:
                        cx = float(p.get("x", 0))
                        cy = float(p.get("y", 0))
                        pw = float(p.get("width", 0))
                        ph = float(p.get("height", 0))
                        x = cx - pw / 2
                        y = cy - ph / 2
                        conv.append({"x": x, "y": y, "width": pw, "height": ph, "class": p.get("class"), "confidence": p.get("confidence")})
                    except Exception:
                        continue
                self._detections = conv
                self.log(f"Received {len(conv)} detections")
                # push to overlay
                try:
                    self.overlay_update(self._detections, self._frame_size)
                except Exception:
                    pass
            except Exception as e:
                self.log(f"Inference error: {e}")
            time.sleep(interval)
