"""Shared HTTP guard for routes that rewrite an existing cluster projection."""
from fastapi import HTTPException

from services import experiment_config


def reject_if_labels_frozen(operation: str) -> None:
    if not experiment_config.FREEZE_LABELS:
        return

    raise HTTPException(
        status_code=423,
        detail={
            "error": "labels_frozen",
            "operation": operation,
            "message": "Cluster labels are frozen for experiment sessions.",
        },
    )
