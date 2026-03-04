"""Logging utilities with correlation-id context."""

import logging
from contextvars import ContextVar, Token

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
_original_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _original_factory(*args, **kwargs)
    record.correlation_id = _correlation_id_ctx.get()
    return record


def configure_logging(level: int = logging.INFO) -> None:
    """Configure process-wide logging once."""
    if getattr(configure_logging, "_configured", False):
        return

    logging.setLogRecordFactory(_record_factory)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [corr:%(correlation_id)s] %(name)s: %(message)s",
    )
    configure_logging._configured = True


def set_correlation_id(correlation_id: str) -> Token:
    """Set correlation id for current context and return reset token."""
    return _correlation_id_ctx.set(correlation_id)


def reset_correlation_id(token: Token) -> None:
    """Reset correlation id context with token."""
    _correlation_id_ctx.reset(token)


def get_correlation_id() -> str:
    """Get current correlation id from context."""
    return _correlation_id_ctx.get()
