"""
Tests for the restocking endpoints: budget-based recommendations and restock orders.

Note: restock_orders is a module-level in-memory list, so orders created here
leak across tests in the same process. Assert membership by order_number,
never on exact list lengths.
"""

import re
from datetime import datetime

import pytest

from restocking import compute_recommendations, lead_time_for


RECOMMENDATIONS_URL = "/api/restocking/recommendations"
ORDERS_URL = "/api/restocking/orders"


def _skus(rows):
    return [r["sku"] for r in rows]


class TestRestockingRecommendations:
    """Tests for GET /api/restocking/recommendations"""

    def test_budget_zero_returns_empty(self, client):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0
        # Every positive-gap forecast is reported as skipped
        assert set(_skus(data["skipped"])) == {
            "WDG-001", "FLT-405", "GSK-203", "BRG-102", "PSU-501", "SNR-420", "VLV-506", "CTL-330"
        }

    def test_large_budget_covers_all_positive_gaps(self, client):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": 1_000_000})
        assert response.status_code == 200
        data = response.json()
        assert data["skipped"] == []
        recs = data["recommendations"]
        assert len(recs) == 8
        for row in recs:
            assert row["gap"] > 0
            assert row["recommended_quantity"] == row["gap"]
            assert row["line_total"] == round(row["gap"] * row["unit_cost"], 2)
        gaps = [r["gap"] for r in recs]
        assert gaps == sorted(gaps, reverse=True)
        # Decreasing-demand item is never recommended
        assert "MTR-304" not in _skus(recs)

    def test_mid_budget_skips_unaffordable_and_continues(self, client):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": 10_000})
        assert response.status_code == 200
        data = response.json()
        rec_skus = _skus(data["recommendations"])
        assert "WDG-001" in _skus(data["skipped"])
        # Cheaper items after the skipped one are still bought
        assert "FLT-405" in rec_skus
        assert "GSK-203" in rec_skus
        assert data["total_cost"] == pytest.approx(5302.98)

    @pytest.mark.parametrize("budget", [500, 1300, 5000, 20000])
    def test_total_cost_never_exceeds_budget(self, client, budget):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": budget})
        assert response.status_code == 200
        data = response.json()
        assert data["budget"] == budget
        assert data["total_cost"] <= budget
        assert data["remaining_budget"] == pytest.approx(round(budget - data["total_cost"], 2))
        assert sum(r["line_total"] for r in data["recommendations"]) == pytest.approx(data["total_cost"])

    def test_response_structure(self, client):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": 20_000})
        row = response.json()["recommendations"][0]
        for field in ("sku", "name", "category", "current_demand", "forecasted_demand", "gap",
                      "unit_cost", "recommended_quantity", "line_total", "lead_time_days"):
            assert field in row

    def test_negative_budget_rejected(self, client):
        response = client.get(RECOMMENDATIONS_URL, params={"budget": -1})
        assert response.status_code == 422

    def test_missing_budget_rejected(self, client):
        response = client.get(RECOMMENDATIONS_URL)
        assert response.status_code == 422

    def test_compute_recommendations_unit(self):
        forecasts = [
            {"item_sku": "B", "item_name": "b", "current_demand": 10, "forecasted_demand": 20,
             "category": "Sensors", "unit_cost": 10.0},           # gap 10, cost 100
            {"item_sku": "A", "item_name": "a", "current_demand": 10, "forecasted_demand": 20,
             "category": "Sensors", "unit_cost": 50.0},           # gap 10, cost 500
            {"item_sku": "C", "item_name": "c", "current_demand": 10, "forecasted_demand": 15,
             "category": "Actuators", "unit_cost": 1.0},          # gap 5, cost 5
            {"item_sku": "D", "item_name": "d", "current_demand": 20, "forecasted_demand": 10,
             "category": "Actuators", "unit_cost": 1.0},          # gap -10, ignored
            {"item_sku": "E", "item_name": "e", "current_demand": 0, "forecasted_demand": 100,
             "category": "Actuators"},                            # no unit_cost, ignored
        ]
        result = compute_recommendations(forecasts, budget=120)
        # Equal gaps tie-break by SKU: A (500) is skipped, then B (100) and C (5) fit
        assert _skus(result["recommendations"]) == ["B", "C"]
        assert _skus(result["skipped"]) == ["A"]
        assert result["total_cost"] == 105
        assert result["remaining_budget"] == 15
        assert result["recommendations"][0]["lead_time_days"] == lead_time_for("Sensors")

    def test_lead_time_default(self):
        assert lead_time_for("Circuit Boards") == 14
        assert lead_time_for("Unknown") == 10
        assert lead_time_for(None) == 10


class TestRestockingOrders:
    """Tests for POST and GET /api/restocking/orders"""

    def _post(self, client, items, warehouse="San Francisco", budget=100_000):
        return client.post(ORDERS_URL, json={"budget": budget, "warehouse": warehouse, "items": items})

    def test_create_order_sets_lead_time_and_delivery(self, client):
        response = self._post(client, [{"sku": "CTL-330", "quantity": 1}])
        assert response.status_code == 201
        order = response.json()
        assert order["status"] == "Submitted"
        assert order["customer"] == "Internal Restock"
        assert order["warehouse"] == "San Francisco"
        assert order["category"] == "Circuit Boards"
        assert order["lead_time_days"] == 14
        assert order["total_value"] == 34.5
        assert re.match(r"^RST-\d{4}-\d{4}$", order["order_number"])
        delivered = datetime.fromisoformat(order["expected_delivery"])
        ordered = datetime.fromisoformat(order["order_date"])
        assert (delivered - ordered).days == 14
        assert order["items"][0]["sku"] == "CTL-330"
        assert order["items"][0]["unit_price"] == 34.5
        assert order["items"][0]["lead_time_days"] == 14

    def test_lead_time_is_max_across_categories(self, client):
        response = self._post(client, [
            {"sku": "SNR-420", "quantity": 2},   # Sensors: 7 days
            {"sku": "WDG-001", "quantity": 3},   # Controllers: 12 days
        ])
        assert response.status_code == 201
        order = response.json()
        assert order["lead_time_days"] == 12
        assert order["category"] == "Mixed"
        assert order["total_value"] == pytest.approx(2 * 89.5 + 3 * 125.0)

    def test_get_orders_returns_created(self, client):
        created = self._post(client, [{"sku": "VLV-506", "quantity": 1}], warehouse="London").json()
        response = client.get(ORDERS_URL)
        assert response.status_code == 200
        assert created["order_number"] in [o["order_number"] for o in response.json()]

    def test_get_orders_warehouse_filter(self, client):
        london = self._post(client, [{"sku": "BRG-102", "quantity": 1}], warehouse="London").json()
        tokyo = self._post(client, [{"sku": "BRG-102", "quantity": 1}], warehouse="Tokyo").json()
        numbers = [o["order_number"] for o in client.get(ORDERS_URL, params={"warehouse": "Tokyo"}).json()]
        assert tokyo["order_number"] in numbers
        assert london["order_number"] not in numbers

    def test_order_numbers_increment(self, client):
        first = self._post(client, [{"sku": "PSU-501", "quantity": 1}]).json()
        second = self._post(client, [{"sku": "PSU-501", "quantity": 1}]).json()
        assert int(second["order_number"][-4:]) == int(first["order_number"][-4:]) + 1

    def test_create_order_empty_items_400(self, client):
        response = self._post(client, [])
        assert response.status_code == 400

    def test_create_order_unknown_sku_400(self, client):
        response = self._post(client, [{"sku": "NOPE-999", "quantity": 1}])
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_create_order_zero_quantity_400(self, client):
        response = self._post(client, [{"sku": "CTL-330", "quantity": 0}])
        assert response.status_code == 400

    def test_create_order_over_budget_400(self, client):
        response = self._post(client, [{"sku": "WDG-001", "quantity": 10}], budget=100)
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]

    def test_restock_orders_not_in_main_orders(self, client):
        created = self._post(client, [{"sku": "GSK-203", "quantity": 1}]).json()
        main_numbers = [o["order_number"] for o in client.get("/api/orders").json()]
        assert created["order_number"] not in main_numbers
