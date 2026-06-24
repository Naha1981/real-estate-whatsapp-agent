"""
Bond Calculator + FLISP Service — mortgage affordability for SA township market.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── FLISP Subsidy Brackets (2026) ────────────────────

FLISP_BRACKETS = [
    {"income_min": 3501, "income_max": 15000, "subsidy": 130000},
    {"income_min": 15001, "income_max": 22000, "subsidy": 90000},
    {"income_min": 22001, "income_max": 30000, "subsidy": 60000},
    {"income_min": 30001, "income_max": 40000, "subsidy": 30000},
]

# ── Bond Constants ────────────────────────────────────

PRIME_RATE = 0.115  # 11.5% prime (2026 estimate)
BOND_TERM_YEARS = 20
MAX_PAYMENT_TO_INCOME = 0.30  # 30% of gross income max


@dataclass
class BondResult:
    max_bond: float
    monthly_repayment: float
    total_cost: float
    deposit_needed: float
    qualifies_flisp: bool
    flisp_amount: float
    flisp_income_bracket: Optional[str]
    monthly_income: float
    warnings: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BondCalculator:
    """Calculates bond affordability and FLISP eligibility."""

    def calculate(self, monthly_income: float, existing_debt: float = 0) -> BondResult:
        """Calculate max bond and check FLISP eligibility."""
        warnings = []

        # Available for bond repayment
        available = (monthly_income * MAX_PAYMENT_TO_INCOME) - existing_debt
        if available <= 0:
            warnings.append("Your existing debt payments are too high relative to income. Consider reducing debt first.")

        available = max(available, 0)

        # Calculate max bond (present value of annuity)
        monthly_rate = PRIME_RATE / 12
        num_payments = BOND_TERM_YEARS * 12

        if monthly_rate > 0:
            max_bond = available * (1 - (1 + monthly_rate) ** (-num_payments)) / monthly_rate
        else:
            max_bond = available * num_payments

        # Monthly repayment on max bond
        monthly_repayment = available

        # Total cost over term
        total_cost = monthly_repayment * num_payments

        # Check FLISP
        flisp_amount = 0
        flisp_bracket = None
        qualifies_flisp = False

        for bracket in FLISP_BRACKETS:
            if bracket["income_min"] <= monthly_income <= bracket["income_max"]:
                qualifies_flisp = True
                flisp_amount = bracket["subsidy"]
                flisp_bracket = f"R{bracket['income_min']:,} – R{bracket['income_max']:,}"
                break

        if qualifies_flisp:
            warnings.append(f"🎉 You qualify for a FLISP subsidy of up to R{flisp_amount:,}!")

        # Deposit (typically 10% for non-FLISP)
        deposit_needed = max_bond * 0.10
        if qualifies_flisp and max_bond <= 500000:
            deposit_needed = 0  # FLISP can cover deposit

        return BondResult(
            max_bond=round(max_bond, -3),  # Round to nearest 1000
            monthly_repayment=round(monthly_repayment),
            total_cost=round(total_cost, -3),
            deposit_needed=round(deposit_needed, -3),
            qualifies_flisp=qualifies_flisp,
            flisp_amount=flisp_amount,
            flisp_income_bracket=flisp_bracket,
            monthly_income=monthly_income,
            warnings=warnings,
        )

    def calculate_for_property(self, monthly_income: float, property_price: float, existing_debt: float = 0) -> BondResult:
        """Calculate if buyer can afford a specific property."""
        result = self.calculate(monthly_income, existing_debt)

        if property_price > result.max_bond + result.flisp_amount:
            shortfall = property_price - result.max_bond - result.flisp_amount
            result.warnings.append(f"⚠️ Shortfall of R{shortfall:,.0f} — you'd need a larger deposit or lower purchase price.")

        return result

    def format_bond_message(self, result: BondResult, property_price: Optional[float] = None) -> str:
        """Format bond result as WhatsApp message."""
        msg = "🏦 *Bond Affordability Check*\n\n"
        msg += f"💰 Monthly Income: R{result.monthly_income:,.0f}\n"
        msg += f"🏠 Max Bond: R{result.max_bond:,.0f}\n"
        msg += f"📅 Monthly Repayment: ~R{result.monthly_repayment:,.0f}\n"
        msg += f"🏧 Deposit Needed: ~R{result.deposit_needed:,.0f}\n"
        msg += f"📊 Term: {BOND_TERM_YEARS} years @ {PRIME_RATE*100:.1f}%\n"

        if property_price:
            total_available = result.max_bond + result.flisp_amount
            if total_available >= property_price:
                msg += f"\n✅ *You can afford R{property_price:,.0f}!*"
            else:
                shortfall = property_price - total_available
                msg += f"\n⚠️ Property is R{shortfall:,.0f} above your max. You'd need a R{shortfall:,.0f} deposit."

        if result.qualifies_flisp:
            msg += f"\n🎉 *FLISP ELIGIBLE!*\n"
            msg += f"   Income bracket: {result.flisp_income_bracket}\n"
            msg += f"   Subsidy amount: Up to R{result.flisp_amount:,.0f}\n"
            msg += f"   _FLISP is a government grant — you don't pay it back!_"

        if result.warnings:
            for w in result.warnings:
                if not w.startswith("🎉"):
                    msg += f"\n{w}"

        msg += f"\n\n💡 *Tip:* Get pre-approved before house hunting. I can connect you with a bond originator — no cost to you."

        return msg


# Singleton
bond_calculator = BondCalculator()
