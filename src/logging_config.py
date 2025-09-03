"""
Logging-Framework für VNB Digitaler.

Zentrale Konfiguration für strukturiertes Logging mit verschiedenen
Log-Levels und Ausgabeformaten.
"""

import json
import logging
import logging.config
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """
    Strukturierter JSON-Formatter für Logs.

    Formatiert Log-Nachrichten als JSON für bessere Auswertbarkeit.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Formatiere Log-Record als JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Exception-Informationen hinzufügen falls vorhanden
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Extra-Felder hinzufügen
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class PipelineLogger:
    """
    Spezialisierter Logger für Datenverarbeitungs-Pipelines.

    Bietet strukturierte Logging-Methoden für Pipeline-Schritte
    mit Kontext-Informationen.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(f"pipeline.{name}")
        self.pipeline_name = name
        self.start_time = None
        self.step_count = 0

    def start_pipeline(self, **context):
        """Starte Pipeline-Logging."""
        self.start_time = datetime.now()
        self.step_count = 0

        self.logger.info(
            "Pipeline gestartet",
            extra={
                "pipeline": self.pipeline_name,
                "event": "pipeline_start",
                **context,
            },
        )

    def step(self, step_name: str, **context):
        """Logge Pipeline-Schritt."""
        self.step_count += 1

        self.logger.info(
            f"Pipeline-Schritt: {step_name}",
            extra={
                "pipeline": self.pipeline_name,
                "event": "pipeline_step",
                "step_name": step_name,
                "step_number": self.step_count,
                **context,
            },
        )

    def success(self, **context):
        """Logge erfolgreichen Pipeline-Abschluss."""
        duration = None
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

        self.logger.info(
            "Pipeline erfolgreich abgeschlossen",
            extra={
                "pipeline": self.pipeline_name,
                "event": "pipeline_success",
                "duration_seconds": duration,
                "total_steps": self.step_count,
                **context,
            },
        )

    def error(self, error_message: str, **context):
        """Logge Pipeline-Fehler."""
        duration = None
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

        self.logger.error(
            f"Pipeline-Fehler: {error_message}",
            extra={
                "pipeline": self.pipeline_name,
                "event": "pipeline_error",
                "error_message": error_message,
                "duration_seconds": duration,
                "failed_at_step": self.step_count,
                **context,
            },
        )

    def data_quality(self, check_name: str, passed: bool, **metrics):
        """Logge Datenqualitäts-Checks."""
        self.logger.info(
            f"Datenqualität: {check_name}",
            extra={
                "pipeline": self.pipeline_name,
                "event": "data_quality_check",
                "check_name": check_name,
                "passed": passed,
                **metrics,
            },
        )


def setup_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    enable_console: bool = True,
    enable_structured: bool = False,
) -> None:
    """
    Konfiguriere Logging für VNB Digitaler.

    Args:
        log_level: Logging-Level (DEBUG, INFO, WARNING, ERROR)
        log_file: Pfad zur Log-Datei (optional)
        enable_console: Console-Logging aktivieren
        enable_structured: JSON-strukturiertes Logging aktivieren
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {},
        "loggers": {
            "vnbdigitaler": {"level": log_level, "handlers": [], "propagate": False},
            "pipeline": {"level": log_level, "handlers": [], "propagate": False},
        },
        "root": {"level": log_level, "handlers": []},
    }

    # Strukturierter Formatter falls aktiviert
    if enable_structured:
        config["formatters"]["structured"] = {"()": StructuredFormatter}

    # Console-Handler
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "structured" if enable_structured else "standard",
            "stream": "ext://sys.stdout",
        }
        config["loggers"]["vnbdigitaler"]["handlers"].append("console")
        config["loggers"]["pipeline"]["handlers"].append("console")
        config["root"]["handlers"].append("console")

    # File-Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "structured" if enable_structured else "detailed",
            "filename": str(log_file),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        config["loggers"]["vnbdigitaler"]["handlers"].append("file")
        config["loggers"]["pipeline"]["handlers"].append("file")
        config["root"]["handlers"].append("file")

    # Logging konfigurieren
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Hole Logger für ein spezifisches Modul.

    Args:
        name: Logger-Name (üblicherweise __name__)

    Returns:
        logging.Logger: Konfigurierter Logger
    """
    return logging.getLogger(f"vnbdigitaler.{name}")


def get_pipeline_logger(pipeline_name: str) -> PipelineLogger:
    """
    Hole Pipeline-Logger.

    Args:
        pipeline_name: Name der Pipeline

    Returns:
        PipelineLogger: Spezialisierter Pipeline-Logger
    """
    return PipelineLogger(pipeline_name)


# Standard-Konfiguration beim Import
if not logging.getLogger().handlers:
    setup_logging()
