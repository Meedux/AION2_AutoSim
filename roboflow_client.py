"""Workflow client using the Roboflow inference-sdk InferenceHTTPClient.

This wrapper writes frame bytes to a temporary file and calls the provided
workflow. It normalizes the returned predictions to a consistent list of dicts.
"""
from typing import Any, Dict, List, Optional, Tuple
import os
import tempfile

try:
    from inference_sdk import InferenceHTTPClient
except Exception:
    InferenceHTTPClient = None  # type: ignore


class WorkflowClient:
    def __init__(self, api_key: str = "nxMk5er0X252GqKpQwBY", api_url: str = "https://serverless.roboflow.com"):
        if InferenceHTTPClient is None:
            raise RuntimeError("inference_sdk not installed. See requirements.txt and pip install inference-sdk")
        self.api_url = api_url.rstrip("/")
        # Default to provided hardcoded API key if environment not set
        self.api_key = api_key
        if not self.api_key:
            raise RuntimeError("ROBOFLOW_API_KEY not set (pass api_key or set env var)")
        self.client = InferenceHTTPClient(api_url=self.api_url, api_key=self.api_key)

    def run_workflow_on_bytes(self, workspace_name: str, workflow_id: str, jpeg_bytes: bytes, use_cache: bool = True) -> Dict[str, Any]:
        # Write bytes to a temp file because the SDK expects a path (safe and simple).
        # On Windows the file must be closed before other libraries can open it, so
        # create a named temp file, close it, call the SDK and then remove it.
        fd, path = tempfile.mkstemp(suffix=".jpg")
        try:
            os.close(fd)
            with open(path, "wb") as f:
                f.write(jpeg_bytes)
                f.flush()
            images = {"image": path}
            result = self.client.run_workflow(
                workspace_name=workspace_name,
                workflow_id=workflow_id,
                images=images,
                use_cache=use_cache,
            )
            return result
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def parse_predictions(self, resp_json: Dict[str, Any], frame_size: Optional[Tuple[int, int]] = None) -> List[Dict[str, Any]]:
        """Attempt to find and normalize detection-like entries from workflow JSON.

        This function is robust: it searches nested structures for lists of dicts
        that look like detection outputs. If coordinates are normalized (0..1)
        they will be scaled using frame_size when provided.
        """
        candidates: List[Dict[str, Any]] = []

        def looks_like_detection(d: Dict[str, Any]) -> bool:
            keys = set(d.keys())
            common = {"x", "y", "width", "height", "bbox", "xmin", "ymin", "xmax", "ymax", "class", "label", "confidence", "score"}
            return len(keys & common) > 0

        def walk(obj: Any):
            if isinstance(obj, dict):
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                if len(obj) > 0 and isinstance(obj[0], dict) and looks_like_detection(obj[0]):
                    for e in obj:
                        if isinstance(e, dict):
                            candidates.append(e)
                else:
                    for item in obj:
                        walk(item)

        walk(resp_json)

        out_list: List[Dict[str, Any]] = []
        fw, fh = (None, None)
        if frame_size:
            fw, fh = frame_size

        for p in candidates:
            # standard fields
            cls = p.get("class") or p.get("label") or p.get("name")
            conf = p.get("confidence") or p.get("score") or p.get("probability")

            # bbox possibilities
            x = p.get("x")
            y = p.get("y")
            w = p.get("width")
            h = p.get("height")

            # bbox as list or dict
            if x is None and "bbox" in p:
                bb = p.get("bbox")
                if isinstance(bb, (list, tuple)) and len(bb) == 4:
                    # assume [xmin, ymin, xmax, ymax]
                    xmin, ymin, xmax, ymax = bb
                    x = xmin
                    y = ymin
                    w = xmax - xmin
                    h = ymax - ymin
                elif isinstance(bb, dict):
                    xmin = bb.get("xmin") or bb.get("x")
                    ymin = bb.get("ymin") or bb.get("y")
                    xmax = bb.get("xmax") or bb.get("x2")
                    ymax = bb.get("ymax") or bb.get("y2")
                    if None not in (xmin, ymin, xmax, ymax):
                        x = xmin
                        y = ymin
                        w = xmax - xmin
                        h = ymax - ymin

            # coordinates as xmin/xmax etc
            if x is None and ("xmin" in p or "x_min" in p):
                xmin = p.get("xmin") or p.get("x_min")
                ymin = p.get("ymin") or p.get("y_min")
                xmax = p.get("xmax") or p.get("x_max")
                ymax = p.get("ymax") or p.get("y_max")
                if None not in (xmin, ymin, xmax, ymax):
                    x = xmin
                    y = ymin
                    w = xmax - xmin
                    h = ymax - ymin

            # If x,y,width,height appear to be center-based (common), convert to top-left later
            # Normalize if values are floats between 0 and 1
            def maybe_scale(val, dim):
                try:
                    if val is None:
                        return None
                    v = float(val)
                    if 0.0 <= v <= 1.0 and dim is not None:
                        return v * dim
                    return v
                except Exception:
                    return None

            if fw and fh:
                x = maybe_scale(x, fw)
                y = maybe_scale(y, fh)
                w = maybe_scale(w, fw)
                h = maybe_scale(h, fh)

            # If we have center-based x,y w,h, convert to top-left
            if x is not None and y is not None and w is not None and h is not None:
                # detect if x,y are centers: if so convert
                # Heuristic: if x+w/2 <= fw then x is center otherwise assume already top-left
                try:
                    xf = float(x)
                    wf = float(w)
                    yf = float(y)
                    hf = float(h)
                    # If x seems to be center (and wf nonzero), convert
                    if fw is None or (0 <= xf - wf / 2 <= (fw if fw else xf)):
                        top_left_x = xf - wf / 2
                        top_left_y = yf - hf / 2
                    else:
                        top_left_x = xf
                        top_left_y = yf
                    out_list.append({
                        "x": top_left_x,
                        "y": top_left_y,
                        "width": wf,
                        "height": hf,
                        "class": cls,
                        "confidence": float(conf) if conf is not None else None,
                    })
                except Exception:
                    continue

        return out_list
