"""The schema of a delivery notice: the interface between the e-mail inbox and the inventory."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str = Field(description="product name, as in the supermarket catalog if possible")
    quantity: float = Field(description="number of units in `unit`")
    unit: Literal["count", "kg", "liter"] = Field(description="convert lb to kg, gallons to count")

    @model_validator(mode="after")
    def plausible(self) -> "LineItem":
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.unit == "count" and not float(self.quantity).is_integer():
            raise ValueError(f"{self.quantity} is not a whole number of items")
        return self


class DeliveryNotice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier: str
    store_city: str
    delivery_date: date
    items: list[LineItem]

    @model_validator(mode="after")
    def not_empty(self) -> "DeliveryNotice":
        if not self.items:
            raise ValueError("a delivery notice needs at least one item")
        return self
