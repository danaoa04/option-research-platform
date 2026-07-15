"""Deterministic walk-forward split generation with no-look-ahead protections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .exceptions import WalkForwardSplitError
from .models import WalkForwardConfig, WalkForwardMode, WalkForwardSplit


@dataclass(slots=True)
class WalkForwardEngine:
    def generate_splits(
        self,
        *,
        start_date: date,
        end_date: date,
        config: WalkForwardConfig,
    ) -> list[WalkForwardSplit]:
        if start_date >= end_date:
            raise WalkForwardSplitError("start_date must be before end_date")
        if config.training_days <= 0 or config.validation_days <= 0 or config.test_days <= 0:
            raise WalkForwardSplitError("training/validation/test days must be positive")
        if config.step_days <= 0:
            raise WalkForwardSplitError("step_days must be positive")

        total_days = (end_date - start_date).days + 1
        minimum_required = config.training_days + config.validation_days + config.test_days
        if total_days < minimum_required:
            return []

        splits: list[WalkForwardSplit] = []
        anchor_start = start_date
        cursor = start_date

        while True:
            train_start = self._train_start(anchor_start, cursor, config.mode)
            train_end = train_start + timedelta(days=config.training_days - 1)

            validation_start = train_end + timedelta(days=1 + config.purge_days)
            validation_end = validation_start + timedelta(days=config.validation_days - 1)

            test_start = validation_end + timedelta(days=1 + config.embargo_days)
            test_end = test_start + timedelta(days=config.test_days - 1)

            if test_end > end_date:
                break

            split_id = f"wf-{len(splits) + 1:04d}"
            split = WalkForwardSplit(
                split_id=split_id,
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
                purge_days=config.purge_days,
                embargo_days=config.embargo_days,
                metadata={"mode": config.mode.value, "regime_aware": config.regime_aware},
            )
            self._validate_no_look_ahead(split)
            splits.append(split)
            cursor = cursor + timedelta(days=config.step_days)

        return splits

    def _train_start(self, anchor: date, cursor: date, mode: WalkForwardMode) -> date:
        if mode == WalkForwardMode.ANCHORED:
            return anchor
        if mode == WalkForwardMode.ROLLING:
            return cursor
        if mode == WalkForwardMode.EXPANDING:
            return anchor
        raise WalkForwardSplitError(f"unsupported walk-forward mode '{mode}'")

    def _validate_no_look_ahead(self, split: WalkForwardSplit) -> None:
        if not (
            split.train_start <= split.train_end < split.validation_start <= split.validation_end
        ):
            raise WalkForwardSplitError("invalid train/validation chronology")
        if not (split.validation_end < split.test_start <= split.test_end):
            raise WalkForwardSplitError("invalid validation/test chronology")
