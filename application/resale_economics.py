"""Economía de reventa: hechos y supuestos permanecen separados."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EbayFeeAssumptions:
    percentage: float
    fixed: float = 0.0
    shipping: float = 0.0
    taxes: float = 0.0
    other: float = 0.0
    acquisition_sales_tax: float = 0.0
    packaging: float = 0.0
    promotion_percentage: float = 0.0

    def __post_init__(self):
        if not 0 <= self.percentage <= 1 or not 0 <= self.promotion_percentage <= 1 or min(self.fixed, self.shipping, self.taxes, self.other, self.acquisition_sales_tax, self.packaging) < 0:
            raise ValueError("Los supuestos de fees y costos deben ser válidos.")


def calculate_resale_economics(cost, resale_price, assumptions):
    if cost is None or resale_price is None:
        return {"status": "unknown", "known": {"cost": cost, "resale_price": resale_price}, "assumptions": assumptions.__dict__.copy()}
    cost, resale_price = float(cost), float(resale_price)
    if cost <= 0 or resale_price <= 0:
        raise ValueError("Costo y precio deben ser mayores que cero.")
    percentage_fee = resale_price * assumptions.percentage
    promotion_fee = resale_price * assumptions.promotion_percentage
    assumed_costs = percentage_fee + promotion_fee + assumptions.fixed + assumptions.shipping + assumptions.taxes + assumptions.other + assumptions.acquisition_sales_tax + assumptions.packaging
    total = cost + assumed_costs
    profit = resale_price - total
    return {
        "status": "estimated", "known": {"cost": cost, "resale_price": resale_price},
        "assumptions": {**assumptions.__dict__, "percentage_fee": round(percentage_fee, 2), "promotion_fee": round(promotion_fee, 2)},
        "costo_total": round(total, 2), "ganancia": round(profit, 2),
        "margen": round(profit / resale_price * 100, 1), "roi": round(profit / cost * 100, 1),
    }
