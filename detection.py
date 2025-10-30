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
                # Log a short preview of raw response for debugging
                try:
                    self.log("Raw workflow response: " + (str(resp)[:1000] + '...') if isinstance(resp, (dict, list, str)) else "(non-json response)")
                except Exception:
                    pass

                # sent frame size (the one we provided to the workflow)
                sent_w, sent_h = (w, h)
                # original window size (overlay size)
                orig_w, orig_h = self.capture.get_window_size() or (w, h)

                preds = self.client.parse_predictions(resp, frame_size=(sent_w, sent_h))

                # scale predictions from sent frame size to original window size
                sx = orig_w / sent_w if sent_w and orig_w else 1.0
                sy = orig_h / sent_h if sent_h and orig_h else 1.0

                conv = []
                for p in preds:
                    try:
                        # parser returns top-left x,y,width,height relative to sent frame
                        x = float(p.get("x", 0)) * sx
                        y = float(p.get("y", 0)) * sy
                        pw = float(p.get("width", 0)) * sx
                        ph = float(p.get("height", 0)) * sy
                        conv.append({"x": x, "y": y, "width": pw, "height": ph, "class": p.get("class"), "confidence": p.get("confidence")})
                    except Exception:
                        continue

                self._detections = conv
                self.log(f"Received {len(conv)} detections (scaled to overlay {orig_w}x{orig_h})")
                # push to overlay (pass overlay target size as orig window size)
                try:
                    self.overlay_update(self._detections, (orig_w, orig_h))
                except Exception:
                    pass
            except Exception as e:
                self.log(f"Inference error: {e}")
            time.sleep(interval)
