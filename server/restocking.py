"""
Restocking logic: budget-constrained recommendations from demand forecasts,
and construction of restock orders with per-category delivery lead times.

Pure functions only (no FastAPI imports) so they can be unit-tested directly.
"""

from datetime import datetime, timedelta
from typing import Optional

# Delivery lead time in days per inventory category.
LEAD_TIME_DAYS = {
    "Circuit Boards": 14,
    "Controllers": 12,
    "Actuators": 10,
    "Power Supplies": 9,
    "Sensors": 7,
}
DEFAULT_LEAD_TIME_DAYS = 10

RESTOCK_CUSTOMER = "Internal Restock"
RESTOCK_STATUS = "Submitted"


def lead_time_for(category: Optional[str]) -> int:
    """Return delivery lead time in days for a category, falling back to the default."""
    return LEAD_TIME_DAYS.get(category or "", DEFAULT_LEAD_TIME_DAYS)


def _gap(forecast: dict) -> int:
    return forecast["forecasted_demand"] - forecast["current_demand"]


def _recommendation_row(forecast: dict, quantity: int) -> dict:
    unit_cost = forecast["unit_cost"]
    return {
        "sku": forecast["item_sku"],
        "name": forecast["item_name"],
        "category": forecast.get("category"),
        "current_demand": forecast["current_demand"],
        "forecasted_demand": forecast["forecasted_demand"],
        "gap": _gap(forecast),
        "unit_cost": unit_cost,
        "recommended_quantity": quantity,
        "line_total": round(quantity * unit_cost, 2),
        "lead_time_days": lead_time_for(forecast.get("category")),
    }


def compute_recommendations(forecasts: list, budget: float) -> dict:
    """
    Greedy budget allocation: candidates are forecasts with a positive demand gap
    and a known unit cost, sorted by largest gap first (SKU as a tie-break for
    determinism). Each candidate is bought in full (the whole gap) if it fits the
    remaining budget; otherwise it is skipped and cheaper candidates are still
    considered. Partial quantities are never recommended.
    """
    candidates = [f for f in forecasts if _gap(f) > 0 and f.get("unit_cost") is not None]
    candidates.sort(key=lambda f: (-_gap(f), f["item_sku"]))

    remaining = float(budget)
    recommendations = []
    skipped = []
    for forecast in candidates:
        row = _recommendation_row(forecast, _gap(forecast))
        # Compare in cents to avoid float drift when a line total exactly equals the remainder
        if round(row["line_total"] * 100) <= round(remaining * 100):
            recommendations.append(row)
            remaining = round(remaining - row["line_total"], 2)
        else:
            skipped.append(row)

    total_cost = round(float(budget) - remaining, 2)
    return {
        "budget": float(budget),
        "total_cost": total_cost,
        "remaining_budget": remaining,
        "recommendations": recommendations,
        "skipped": skipped,
    }


def build_restock_order(items: list, forecasts: list, warehouse: str, budget: float,
                        sequence: int, now: Optional[datetime] = None) -> dict:
    """
    Build a restock order dict compatible with the Order model.

    `items` is a list of {"sku", "quantity"}; prices and names are always taken
    from `forecasts` so the client cannot submit its own pricing.
    Raises ValueError for empty items, unknown SKUs, non-positive quantities,
    or a total that exceeds the budget.
    """
    if not items:
        raise ValueError("Order must contain at least one item")

    now = (now or datetime.now()).replace(microsecond=0)
    by_sku = {f["item_sku"]: f for f in forecasts}

    order_items = []
    for item in items:
        forecast = by_sku.get(item["sku"])
        if forecast is None or forecast.get("unit_cost") is None:
            raise ValueError(f"Unknown SKU: {item['sku']}")
        quantity = int(item["quantity"])
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive for SKU {item['sku']}")
        order_items.append({
            "sku": forecast["item_sku"],
            "name": forecast["item_name"],
            "quantity": quantity,
            "unit_price": forecast["unit_cost"],
            "category": forecast.get("category"),
            "lead_time_days": lead_time_for(forecast.get("category")),
        })

    total_value = round(sum(i["quantity"] * i["unit_price"] for i in order_items), 2)
    if round(total_value * 100) > round(float(budget) * 100):
        raise ValueError(f"Order total {total_value} exceeds budget {budget}")

    # The order arrives when its slowest line arrives
    lead_time_days = max(i["lead_time_days"] for i in order_items)
    categories = {i["category"] for i in order_items}
    category = categories.pop() if len(categories) == 1 else "Mixed"

    return {
        "id": f"restock-{sequence}",
        "order_number": f"RST-{now.year}-{sequence:04d}",
        "customer": RESTOCK_CUSTOMER,
        "items": order_items,
        "status": RESTOCK_STATUS,
        "order_date": now.isoformat(),
        "expected_delivery": (now + timedelta(days=lead_time_days)).isoformat(),
        "actual_delivery": None,
        "warehouse": warehouse,
        "category": category,
        "total_value": total_value,
        "lead_time_days": lead_time_days,
        "budget": float(budget),
    }
