"""Local model client using Ultralytics YOLO (PyTorch .pt weights).

Loads a local `models/aion.pt` weight and exposes a predict(frame) method.
The predict method returns a list of detections as dicts with top-left x,y,width,height
in the coordinates of the provided frame.
"""
from typing import List, Dict, Optional
import os
import numpy as np

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None  # type: ignore


class LocalModelClient:
    def __init__(self, weights_path: str = "models/aion.pt", device: Optional[str] = None, imgsz: int = 640):
        if YOLO is None:
            raise RuntimeError("ultralytics not installed. Install via `pip install ultralytics`")
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Weights not found: {weights_path}")
        self.weights_path = weights_path
        self.model = YOLO(weights_path)
        # device selection handled by ultralytics automatically; user can set CUDA env or torch device
        self.imgsz = imgsz

    def predict(self, frame: np.ndarray) -> List[Dict]:
        """Run inference on a BGR numpy array (H,W,3). Returns list of detections with
        top-left x,y,width,height relative to the input frame passed to this function.
        """
        # Ultralytics accepts BGR/np arrays directly
        results = self.model(frame, imgsz=self.imgsz)
        if not results or len(results) == 0:
            return []
        r = results[0]
        # get class name mapping if available
        names = None
        try:
            names = getattr(r, "names", None) or getattr(self.model, "names", None)
        except Exception:
            names = None

        # Use pandas output for convenience
        try:
            df = r.pandas().xyxy[0]
        except Exception:
            # fallback: try boxes
            boxes = getattr(r, "boxes", None)
            if boxes is None:
                return []
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy() if hasattr(boxes, "conf") else [0.0] * len(xyxy)
            classes = boxes.cls.cpu().numpy() if hasattr(boxes, "cls") else [None] * len(xyxy)
            out = []
            for i, xy in enumerate(xyxy):
                xmin, ymin, xmax, ymax = xy.tolist()
                w = xmax - xmin
                h = ymax - ymin
                # map numeric class index to human-readable name when possible
                cls_val = classes[i]
                try:
                    cls_idx = int(cls_val) if cls_val is not None else None
                except Exception:
                    cls_idx = None
                if names and cls_idx is not None and cls_idx in names:
                    cls_name = str(names[cls_idx])
                else:
                    cls_name = str(cls_val)
                out.append({"x": xmin, "y": ymin, "width": w, "height": h, "class": cls_name, "confidence": float(confs[i])})
            return out

        out = []
        for _, row in df.iterrows():
            xmin = float(row["xmin"]) if "xmin" in row.index else float(row["x1"]) if "x1" in row.index else None
            ymin = float(row["ymin"]) if "ymin" in row.index else float(row["y1"]) if "y1" in row.index else None
            xmax = float(row["xmax"]) if "xmax" in row.index else float(row["x2"]) if "x2" in row.index else None
            ymax = float(row["ymax"]) if "ymax" in row.index else float(row["y2"]) if "y2" in row.index else None
            if None in (xmin, ymin, xmax, ymax):
                continue
            w = xmax - xmin
            h = ymax - ymin
            name = str(row["name"]) if "name" in row.index else str(row.get("class", ""))
            conf = float(row["confidence"]) if "confidence" in row.index else float(row.get("conf", 0.0))
            out.append({"x": xmin, "y": ymin, "width": w, "height": h, "class": name, "confidence": conf})
        return out
