"""Detection controller: ties capture, workflow client, and overlay together."""
import threading
import time
from typing import Callable
from loguru import logger
from capture import CaptureWorker
from model_client import LocalModelClient
from action_planner import ActionPlanner
from stealth_config import stealth
from utils import get_window_rect
# utils helpers (no jpeg encode needed for local model)


class DetectionController:
    def __init__(self, hwnd: int, overlay_update: Callable, log_fn: Callable, fps: int = 10):
        """overlay_update(detections, (w,h)) will be called on each new result or tick.
        log_fn(text) will be called to output logs to UI.
        """
        self.hwnd = hwnd
        self.overlay_update = overlay_update
        self.log = log_fn
        # Use stealth FPS to reduce detection frequency and avoid anti-cheat
        self.fps = stealth.get_detection_fps()
        self.log(f"Detection FPS set to {self.fps} (stealth mode)")
        logger.info(f"🕵️ Stealth mode enabled: FPS={self.fps}, randomized timing, human-like behavior")

        # keep capture at original size (no forced resize) to preserve mapping accuracy;
        # we'll make a resized copy for the model if needed inside the model client.
        self.capture = CaptureWorker(hwnd=hwnd, target_fps=max(5, fps * 2), resize_max=None)
        # local model uses models/aion.pt in repo
        self.client = LocalModelClient(weights_path="models/aion.pt")
        # action planner will perform input actions (double-click / movement)
        # Enabled by default per user request; main window will also apply its stored preference.
        self.action_planner = ActionPlanner(hwnd=hwnd, enabled=True)

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
                # We run the local model on a resized copy for speed, then map detections
                # back to the original window coordinates.
                orig_w, orig_h = self.capture.get_window_size() or (w, h)
                frame_for_model = frame.copy()
                # Let the model client decide resizing via its imgsz; but we will pass the frame_for_model as-is.
                preds = self.client.predict(frame_for_model)

                sent_h, sent_w = frame_for_model.shape[:2]
                sx = orig_w / sent_w if sent_w and orig_w else 1.0
                sy = orig_h / sent_h if sent_h and orig_h else 1.0

                conv = []
                for p in preds:
                    try:
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
                # execute action planner (navigate / attack) -- pass full window rect
                try:
                    rect = get_window_rect(self.hwnd)
                    if rect:
                        left, top, rw, rh = rect
                        self.action_planner.plan_and_execute(self._detections, (left, top, rw, rh))
                    else:
                        # fallback: use origin at (0,0) + orig sizes
                        self.action_planner.plan_and_execute(self._detections, (0, 0, orig_w, orig_h))
                except Exception as e:
                    # action planner errors should not stop the detection loop
                    self.log(f"Action planner error: {e}")
            except Exception as e:
                self.log(f"Inference error: {e}")
            time.sleep(interval)
