"""Workflow client using the Roboflow inference-sdk InferenceHTTPClient.

This wrapper writes frame bytes to a temporary file and calls the provided
workflow. It normalizes the returned predictions to a consistent list of dicts.
"""
from typing import Any, Dict, List, Optional
import os
import tempfile

try:
    from inference_sdk import InferenceHTTPClient
except Exception:
    InferenceHTTPClient = None  # type: ignore


class WorkflowClient:
    def __init__(self, api_key: Optional[str] = None, api_url: str = "https://serverless.roboflow.com"):
        if InferenceHTTPClient is None:
            raise RuntimeError("inference_sdk not installed. See requirements.txt and pip install inference-sdk")
        self.api_url = api_url.rstrip("/")
        # Default to provided hardcoded API key if environment not set
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY") or "nxMk5er0X252GqKpQwBY"
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

    def parse_predictions(self, resp_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Attempt to find predictions in common keys
        preds = []
        if not isinstance(resp_json, dict):
            return preds
        # Roboflow workflows may put model outputs under 'outputs' or 'predictions'
        if "predictions" in resp_json and isinstance(resp_json["predictions"], list):
            preds = resp_json["predictions"]
        elif "outputs" in resp_json:
            # outputs may be nested
            out = resp_json["outputs"]
            if isinstance(out, dict) and "predictions" in out:
                preds = out.get("predictions", [])
            elif isinstance(out, list) and len(out) > 0 and isinstance(out[0], dict):
                # try to find a predictions key inside
                for entry in out:
                    if "predictions" in entry and isinstance(entry["predictions"], list):
                        preds = entry["predictions"]
                        break

        # Normalize
        out_list: List[Dict[str, Any]] = []
        for p in preds:
            out_list.append({
                "x": p.get("x"),
                "y": p.get("y"),
                "width": p.get("width"),
                "height": p.get("height"),
                "class": p.get("class") or p.get("label") or p.get("name"),
                "confidence": p.get("confidence") or p.get("score") or p.get("probability")
            })
        return out_list
