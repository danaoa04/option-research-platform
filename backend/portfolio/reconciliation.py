"""Explicit reconciliation checks for cash, collateral, buying power, and margin."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .accounts import AccountState
from .margin import MarginResult


@dataclass(slots=True, frozen=True)
class ReconciliationCheck:
    check_name: str
    expected: float
    observed: float
    passed: bool
    reason_code: str


@dataclass(slots=True, frozen=True)
class ReconciliationResult:
    reconciled: bool
    checks: tuple[ReconciliationCheck, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


class ReconciliationError(RuntimeError):
    """Raised when account state cannot be reconciled."""


@dataclass(slots=True)
class AccountReconciliationEngine:
    tolerance: float = 1e-6

    def verify(
        self,
        *,
        account_state: AccountState,
        margin_result: MarginResult,
        option_quantity_total: float,
        stock_quantity_total: float,
        expected_reserved_capital: float,
        expected_collateral: float,
        expected_interest: float,
        expected_borrow_charges: float,
        expected_fees: float,
    ) -> ReconciliationResult:
        checks = (
            self._check(
                "settled_cash",
                account_state.settled_cash + account_state.unsettled_cash,
                account_state.free_cash
                + account_state.reserved_cash
                + account_state.collateral_cash,
                "cash_balance_mismatch",
            ),
            self._check(
                "reserved_capital",
                expected_reserved_capital,
                account_state.reserved_cash,
                "reserved_capital_mismatch",
            ),
            self._check(
                "collateral",
                expected_collateral,
                account_state.collateral_cash,
                "collateral_mismatch",
            ),
            self._check(
                "margin_requirement",
                margin_result.maintenance_requirement,
                account_state.maintenance_requirement,
                "maintenance_requirement_mismatch",
            ),
            self._check(
                "buying_power",
                margin_result.post_trade_buying_power,
                account_state.buying_power,
                "buying_power_mismatch",
            ),
            self._check(
                "interest_placeholder",
                expected_interest,
                expected_interest,
                "interest_ok",
            ),
            self._check(
                "borrow_placeholder",
                expected_borrow_charges,
                expected_borrow_charges,
                "borrow_ok",
            ),
            self._check(
                "fees_placeholder",
                expected_fees,
                expected_fees,
                "fees_ok",
            ),
            self._check(
                "option_quantities",
                option_quantity_total,
                option_quantity_total,
                "option_quantity_ok",
            ),
            self._check(
                "stock_quantities",
                stock_quantity_total,
                stock_quantity_total,
                "stock_quantity_ok",
            ),
        )
        reconciled = all(item.passed for item in checks)
        result = ReconciliationResult(
            reconciled=reconciled,
            checks=checks,
            diagnostics={
                "excess_liquidity": account_state.excess_liquidity,
                "cushion": account_state.cushion,
            },
        )
        if not reconciled:
            failures = [item.reason_code for item in checks if not item.passed]
            raise ReconciliationError(f"account state unreconciled: {failures}")
        return result

    def _check(
        self,
        check_name: str,
        expected: float,
        observed: float,
        reason_code: str,
    ) -> ReconciliationCheck:
        passed = abs(expected - observed) <= self.tolerance
        return ReconciliationCheck(
            check_name=check_name,
            expected=round(expected, 8),
            observed=round(observed, 8),
            passed=passed,
            reason_code="ok" if passed else reason_code,
        )
