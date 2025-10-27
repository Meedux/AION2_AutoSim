"""models.py
ML model placeholders for training and inference.

This module is intentionally generic so you can wire scikit-learn or PyTorch
models here later. For now it provides stubs for train/predict/save/load.
"""
from __future__ import annotations
from typing import Any, Dict
import logging
import pickle

logger = logging.getLogger(__name__)


class DummyModel:
    def fit(self, X, y):
        logger.info("DummyModel.fit called with %d samples", len(X) if X else 0)

    def predict(self, X):
        logger.info("DummyModel.predict called with %d samples", len(X) if X else 0)
        return [0 for _ in (X or [])]


class ModelManager:
    def __init__(self):
        self.model = DummyModel()

    def train(self, data: Dict[str, Any]) -> None:
        # placeholder: data should contain X,y
        X = data.get("X")
        y = data.get("y")
        self.model.fit(X, y)

    def predict(self, state: Dict[str, Any]) -> Any:
        return self.model.predict([state])

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info("Saved model to %s", path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        logger.info("Loaded model from %s", path)
