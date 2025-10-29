"""Detector module (template + OCR + optional model fusion)

This replacement provides:
- TemplateManager: loads user templates from ./templates/{map,hp_mp,nameplates}
- Multi-scale template matching plus ORB fallback
- OCR via pytesseract when available
- Optional YOLO fusion when ultralytics and model are provided
- Produces detection dicts consumed by overlay/main
"""

import os
import time
import threading
from typing import List, Tuple, Dict, Optional

import numpy as np
import cv2
import mss
from loguru import logger

# Optional OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    pytesseract = None
    OCR_AVAILABLE = False

# Optional YOLO
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class TemplateManager:
    def __init__(self, templates_dir: str = None):
        self.base = templates_dir or os.path.join(os.getcwd(), 'templates')
        self.templates = {
            'map': [],
            'hp_mp': [],
            'nameplates': []
        }
        self._load_templates()

    def _load_templates(self):
        for key in list(self.templates.keys()):
            folder = os.path.join(self.base, key)
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                p = os.path.join(folder, fn)
                if not os.path.isfile(p):
                    continue
                img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
                if img is None:
                    continue
                self.templates[key].append({'name': fn, 'img': img})
            logger.info(f'Loaded {len(self.templates[key])} templates for {key} from {folder}')

    def get(self, key: str) -> List[Dict]:
        return self.templates.get(key, [])


def _multi_scale_match(img_gray: np.ndarray, tpl_gray: np.ndarray, scales=(0.9, 1.0, 1.1), method=cv2.TM_CCOEFF_NORMED):
    """Try matching template at multiple scales; return best (score, x, y, w, h) or None."""
    ih, iw = img_gray.shape[:2]
    th, tw = tpl_gray.shape[:2]
    best = None
    for s in scales:
        sw = int(round(tw * s))
        sh = int(round(th * s))
        if sw < 8 or sh < 6 or sw >= iw or sh >= ih:
            continue
        tpl_rs = cv2.resize(tpl_gray, (sw, sh), interpolation=cv2.INTER_LINEAR)
        res = cv2.matchTemplate(img_gray, tpl_rs, method)
        minv, maxv, minloc, maxloc = cv2.minMaxLoc(res)
        # TM_CCOEFF_NORMED: higher is better
        score = maxv
        if best is None or score > best[0]:
            best = (score, maxloc[0], maxloc[1], sw, sh)
    return best


def _orb_match(img: np.ndarray, tpl: np.ndarray, min_matches=6):
    """Fallback ORB feature matching; returns bounding box in img coords or None."""
    try:
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY), None)
        kp2, des2 = orb.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        if len(matches) < min_matches:
            return None
        pts_tpl = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts_img = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(pts_tpl, pts_img, cv2.RANSAC, 5.0)
        if H is None:
            return None
        h, w = tpl.shape[:2]
        corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(corners, H)
        xs = projected[:, 0, 0]
        ys = projected[:, 0, 1]
        x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        return (x1, y1, x2, y2)
    except Exception:
        return None


class Detector:
    def __init__(self, model_path: Optional[str] = None, target_label: Optional[str] = None,
                 templates_dir: Optional[str] = None, conf_thr: float = 0.35):
        self.model_path = model_path
        self.target_label = target_label
        self.conf_thr = conf_thr
        self.running = False
        self._thread = None
        self._model = None
        self._tplmgr = TemplateManager(templates_dir)
        self._cache = {}  # simple cache for template matches: key->(timestamp, result)
        self._cache_ttl = 0.5  # seconds

    def load_model(self):
        if YOLO is None or not self.model_path:
            logger.info('YOLO model not available or not provided; skipping model load')
            self._model = None
            return
        try:
            self._model = YOLO(self.model_path)
            logger.info('YOLO model loaded')
        except Exception as e:
            logger.exception('Failed to load YOLO model: {}', e)
            self._model = None

    def _get_cache(self, key):
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, val = entry
        if time.time() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return val

    def _set_cache(self, key, val):
        self._cache[key] = (time.time(), val)

    def _match_map(self, img_gray: np.ndarray) -> Optional[Tuple[int, int, int, int, float]]:
        """Try to find minimap via templates in the bottom-right region first."""
        key = 'map_br'
        cached = self._get_cache(key)
        if cached:
            return cached
        h, w = img_gray.shape[:2]
        # search region bottom-right (adjustable)
        sx = int(w * 0.55)
        sy = int(h * 0.45)
        crop = img_gray[sy:h, sx:w]
        best_overall = None
        for tpl in self._tplmgr.get('map'):
            tpl_img = tpl['img']
            if tpl_img is None:
                continue
            tpl_gray = cv2.cvtColor(tpl_img, cv2.COLOR_BGR2GRAY) if tpl_img.ndim == 3 else tpl_img
            best = _multi_scale_match(crop, tpl_gray, scales=(0.9, 1.0, 1.1))
            if best and (best_overall is None or best[0] > best_overall[0]):
                score, mx, my, mw, mh = best
                # convert to full image coords
                ax = sx + mx
                ay = sy + my
                best_overall = (score, ax, ay, mw, mh)
        if best_overall:
            self._set_cache(key, best_overall)
        return best_overall

    def _match_hp_mp_templates(self, img_gray: np.ndarray) -> List[Dict]:
        """Search for hp/mp templates across the top-left HUD region by default.
        Returns list of dicts {'type':'hp'/'mp','box':(x1,y1,x2,y2),'score':float}
        """
        key = 'hp_mp'
        cached = self._get_cache(key)
        if cached:
            return cached
        h, w = img_gray.shape[:2]
        # common HUD area: lower-left; allow searching more widely
        sx = 0
        sy = int(h * 0.6)
        ex = int(w * 0.5)
        ey = h
        crop = img_gray[sy:ey, sx:ex]
        matches = []
        for tpl in self._tplmgr.get('hp_mp'):
            tpl_img = tpl['img']
            if tpl_img is None:
                continue
            tpl_gray = cv2.cvtColor(tpl_img, cv2.COLOR_BGR2GRAY) if tpl_img.ndim == 3 else tpl_img
            best = _multi_scale_match(crop, tpl_gray, scales=(0.9, 1.0, 1.1))
            if best:
                score, mx, my, mw, mh = best
                ax = sx + mx
                ay = sy + my
                matches.append({'name': tpl['name'], 'type': 'hp_mp', 'box': (ax, ay, ax + mw, ay + mh), 'score': float(score)})
        self._set_cache(key, matches)
        return matches

    def _ocr_read(self, img_crop: np.ndarray) -> Optional[str]:
        if not OCR_AVAILABLE:
            return None
        try:
            gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
            # upscale small crops to help OCR
            h, w = gray.shape[:2]
            if h < 18:
                gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
            # adaptive threshold
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            config = '--psm 7 --oem 3'
            text = pytesseract.image_to_string(th, config=config).strip()
            if not text:
                return None
            # simple cleanup
            text = text.replace('\n', ' ').strip()
            return text
        except Exception:
            return None

    def _estimate_fill_from_bar(self, bar_crop: np.ndarray, color='red') -> Optional[float]:
        # expects bar_crop in BGR
        try:
            hsv = cv2.cvtColor(bar_crop, cv2.COLOR_BGR2HSV)
            if color == 'red':
                lower1 = np.array([0, 100, 80])
                upper1 = np.array([10, 255, 255])
                lower2 = np.array([160, 100, 80])
                upper2 = np.array([179, 255, 255])
                mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
            else:
                lower = np.array([90, 80, 60])
                upper = np.array([140, 255, 255])
                mask = cv2.inRange(hsv, lower, upper)
            # reduce noise
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            m = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
            cols = cv2.reduce(m, 0, cv2.REDUCE_SUM, dtype=cv2.CV_32S).reshape(-1)
            if cols.size == 0:
                return None
            # consider columns with >10% rows as filled
            row_count = m.shape[0]
            col_filled = cols > (row_count * 255 * 0.08)
            if not col_filled.any():
                return None
            # detect span
            idxs = np.where(col_filled)[0]
            span = idxs[-1] - idxs[0] + 1
            filled = float(np.sum(col_filled)) / float(span)
            # additional sanity clamping
            return max(0.0, min(1.0, filled))
        except Exception:
            return None

    def start(self, capture_rect: Tuple[int, int, int, int], on_detect):
        if self.running:
            return
        self.capture_rect = capture_rect
        self.on_detect = on_detect
        self.running = True
        self.load_model()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_loop(self, capture_rect=None, on_detect=None):
        left, top, right, bottom = self.capture_rect
        width = right - left
        height = bottom - top
        sct = mss.mss()
        monitor = {'top': top, 'left': left, 'width': width, 'height': height}
        logger.info('Detector loop started')
        while self.running:
            t0 = time.time()
            s = sct.grab(monitor)
            frame = np.array(s)
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            detections: List[Dict] = []

            # 1) Map detection via templates (fast, bottom-right)
            map_match = self._match_map(frame_gray)
            if map_match:
                score, ax, ay, mw, mh = map_match
                # compute circle approximation from template box
                cx = ax + mw // 2
                cy = ay + mh // 2
                r = max(mw, mh) // 2
                detections.append({'label': 'map', 'box': (ax, ay, ax + mw, ay + mh), 'circle': (cx, cy, r), 'template_score': float(score)})

            # 2) HP/MP bars via templates (search HUD region)
            hpmp_matches = self._match_hp_mp_templates(frame_gray)
            for m in hpmp_matches:
                bx1, by1, bx2, by2 = m['box']
                crop = frame[by1:by2, bx1:bx2]
                # try both colors
                hp = self._estimate_fill_from_bar(crop, color='red')
                mp = self._estimate_fill_from_bar(crop, color='blue')
                det = {'label': 'hp_mp', 'box': (bx1, by1, bx2, by2), 'template_score': m['score']}
                if hp is not None:
                    det['hp_pct'] = hp
                if mp is not None:
                    det['mp_pct'] = mp
                detections.append(det)

            # 3) Nameplate detection: color heuristics + OCR
            # use existing _find_text_regions code (color heuristics) for speed
            name_regs = self._find_text_regions(frame)
            for reg in name_regs:
                x1, y1, x2, y2 = reg['box']
                crop = frame[y1:y2, x1:x2]
                text = reg.get('text')
                if text is None and OCR_AVAILABLE:
                    text = self._ocr_read(crop)
                det = {'label': text or 'name', 'box': (x1, y1, x2, y2)}
                # detect target ring under the mob
                if self._detect_target_ring(frame, (x1, y1, x2, y2)):
                    det['is_targeted'] = True
                # also estimate small HP/MP bars near nameplate
                hp, mp = self._estimate_bars(frame, x1, y1, x2, y2)
                if hp is not None:
                    det['hp_pct'] = hp
                if mp is not None:
                    det['mp_pct'] = mp
                detections.append(det)

            # 4) Optional: run YOLO model and merge detections
            if self._model is not None:
                try:
                    results = self._model(frame, conf=self.conf_thr, stream=False)
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
                except Exception as e:
                    logger.debug('YOLO inference error: {}', e)

            # 5) Pick primary target (if any) for callback: prefer name matches to target_label
            primary = None
            if self.target_label:
                for d in detections:
                    lab = d.get('label') or ''
                    if lab and isinstance(lab, str) and self.target_label.lower() in lab.lower():
                        primary = d
                        break
            if primary is None and detections:
                # choose largest bbox area
                primary = max(detections, key=lambda d: (d['box'][2] - d['box'][0]) * (d['box'][3] - d['box'][1]))

            # callback with absolute screen coords for primary center
            if primary is not None:
                bx1, by1, bx2, by2 = primary['box']
                cx = int((bx1 + bx2) / 2) + left
                cy = int((by1 + by2) / 2) + top
                try:
                    # call user callback with (detection_dict, (cx,cy), frame, detections)
                    self.on_detect(primary, (cx, cy), frame, detections)
                except Exception:
                    logger.exception('on_detect handler raised')

            # timing and sleep to keep ~30 FPS max
            elapsed = time.time() - t0
            time.sleep(max(0.001, 0.03 - elapsed))
