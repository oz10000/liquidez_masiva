# liquidez_masiva/core/logging_utils.py
"""
Logger thread-safe con rotación a archivo + salida a stderr.
Formato opcional JSON para ingestión por herramientas de observabilidad.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k not in ("name", "msg", "args", "levelname", "levelno",
                         "pathname", "filename", "module", "exc_info",
                         "exc_text", "stack_info", "lineno", "funcName",
                         "created", "msecs", "relativeCreated", "thread",
                         "threadName", "processName", "process", "message"):
                payload[k] = v
        return json.dumps(payload, ensure_ascii=True)


def get_logger(
    name: str = "liquidez_masiva",
    log_dir: str | Path = "logs",
    level: int = logging.INFO,
    json_format: bool = False,
) -> logging.Logger:
    """
    Devuelve un logger configurado. Idempotente: llamar 2 veces no duplica handlers.
    """
    logger = logging.getLogger(name)
    if getattr(logger, "_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = False

    stream = logging.StreamHandler(sys.stderr)
    if json_format:
        stream.setFormatter(_JsonFormatter())
    else:
        stream.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    logger.addHandler(stream)

    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            Path(log_dir) / f"{name}.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        if json_format:
            fh.setFormatter(_JsonFormatter())
        else:
            fh.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
        logger.addHandler(fh)
    except Exception:
        # Si el FS es read-only (Android restrictivo), continuar sin file handler
        pass

    logger._configured = True  # type: ignore[attr-defined]
    return logger
