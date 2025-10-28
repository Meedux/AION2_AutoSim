import time
import threading
import numpy as np
import mss
import cv2
from loguru import logger

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class Detector:
    """Runs capture + model inference on a window region.

    Usage:
      det = Detector(model_path='best.pt', target_label='Highland Sparkle')
      det.start(capture_rect=(left,top,right,bottom), on_detect=callback)
    """

    def __init__(self, model_path: str = None, target_label: str = None, conf_thr: float = 0.4):
        self.model_path = model_path
        self.target_label = target_label
        self.conf_thr = conf_thr
        self.running = False
        self._thread = None
        self._model = None

    def load_model(self):
        if YOLO is None:
            logger.warning('ultralytics YOLO not available; using lightweight color-based fallback detector')
            self._fallback = True
            return
        if not self.model_path:
            raise ValueError('model_path must be provided')
        logger.info(f'Loading model from: {self.model_path}')
        try:
            self._model = YOLO(self.model_path)
            self._fallback = False
        except Exception as e:
            logger.exception('Failed to load YOLO model: {}', e)
            logger.warning('Falling back to lightweight color-based detector')
            self._fallback = True

    def start(self, capture_rect, on_detect):
        if self.running:
            return
        self.running = True
        if self._model is None:
            self.load_model()
        self._thread = threading.Thread(target=self._run_loop, args=(capture_rect, on_detect), daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_loop(self, capture_rect, on_detect):
        left, top, right, bottom = capture_rect
        width = right - left
        height = bottom - top
        sct = mss.mss()
        monitor = {'top': top, 'left': left, 'width': width, 'height': height}

        logger.info('Starting capture + inference loop')
        while self.running:
            start = time.time()
            s = sct.grab(monitor)
            img = np.array(s)
            # BGRA -> BGR
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            detections = []
            target = None
            if not getattr(self, '_fallback', False):
                # Run model inference
                try:
                    results = self._model(img, conf=self.conf_thr, stream=False)
                except Exception as e:
                    logger.exception('Model inference error: {}', e)
                    results = []

                # Parse results
                for r in results:
                    boxes = getattr(r, 'boxes', None)
                    if boxes is None:
                        continue
                    xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes, 'xyxy') else []
                    confs = boxes.conf.cpu().numpy() if hasattr(boxes, 'conf') else []
                    cls_idxs = boxes.cls.cpu().numpy().astype(int) if hasattr(boxes, 'cls') else []
                    names = getattr(self._model, 'names', {})

                    for bb, conf, cls_idx in zip(xyxy, confs, cls_idxs):
                        class_name = names.get(int(cls_idx), str(cls_idx))
                        x1, y1, x2, y2 = map(int, bb)
                        detections.append({'label': class_name, 'conf': float(conf), 'box': (x1, y1, x2, y2)})

                # Find target detections
                for d in detections:
                    if self.target_label is None or d['label'] == self.target_label:
                        target = d
                        break
            else:
                # Lightweight fallback: detect yellow-ish text/regions (heuristic)
                try:
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    # Yellow range — tuned for typical UI nameplates (may need adjustment)
                    lower = np.array([15, 120, 120])
                    upper = np.array([40, 255, 255])
                    mask = cv2.inRange(hsv, lower, upper)
                    # Morphological clean
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    h_img, w_img = mask.shape[:2]
                    for cnt in contours:
                        x, y, w, h = cv2.boundingRect(cnt)
                        area = w * h
                        if area < (w_img * h_img) * 0.0005:
                            continue
                        # Expand box a bit
                        pad = int(max(4, min(w, h) * 0.2))
                        x1 = max(0, x - pad)
                        y1 = max(0, y - pad)
                        x2 = min(w_img - 1, x + w + pad)
                        y2 = min(h_img - 1, y + h + pad)
                        detections.append({'label': self.target_label or 'target', 'conf': 0.5, 'box': (x1, y1, x2, y2)})
                    # pick the largest detection as target
                    if detections:
                        target = max(detections, key=lambda d: (d['box'][2] - d['box'][0]) * (d['box'][3] - d['box'][1]))
                except Exception as e:
                    logger.exception('Fallback detection error: {}', e)

            if target is not None:
                # Convert to absolute screen coordinates
                x1, y1, x2, y2 = target['box']
                cx = int((x1 + x2) / 2) + left
                cy = int((y1 + y2) / 2) + top
                on_detect(target, (cx, cy), img, detections)

            elapsed = time.time() - start
            # Limit loop to reasonable FPS, but keep responsive
            time.sleep(max(0.001, 0.03 - elapsed))
