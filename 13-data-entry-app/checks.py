"""Checks for a new product entered by store staff: schema errors block, plausibility warns."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from rapidfuzz import fuzz, process

from inventory_data.master import DENSITY_KG_PER_L, gtin_is_valid

Category = Literal["produce", "dairy", "bakery", "meat", "seafood", "beverages", "pantry",
                   "frozen", "household", "refill"]
UNITS_BY_CATEGORY = {"produce": {"count", "kg"}, "meat": {"count", "kg"},
                     "seafood": {"count", "kg"}, "refill": {"liter"}}


class NewProduct(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    gtin: str = Field(pattern=r"^\d{13}$", description="13 digits, with the leading zero")
    category: Category
    unit: Literal["count", "kg", "liter"]
    unit_price: float = Field(gt=0, le=500)
    supplier_id: int
    case_pack: int = Field(ge=1, le=200)
    case_length_cm: float = Field(gt=0, le=200)
    case_width_cm: float = Field(gt=0, le=200)
    case_height_cm: float = Field(gt=0, le=200)
    unit_weight_kg: float = Field(gt=0, le=50)
    shelf_life_days: int = Field(ge=1, le=1825)


@dataclass
class Finding:
    level: Literal["error", "warning"]
    field: str
    message: str


def check(values: dict, catalog: pd.DataFrame) -> list[Finding]:
    try:
        p = NewProduct(**values)
    except ValidationError as e:
        return [Finding("error", ".".join(map(str, err["loc"])), err["msg"]) for err in e.errors()]

    found = []
    if not gtin_is_valid(p.gtin):
        found.append(Finding("error", "gtin", "the check digit is wrong (typo?)"))
    if p.gtin in set(catalog.gtin):
        other = catalog.set_index("gtin").name[p.gtin]
        found.append(Finding("error", "gtin", f"this GTIN already belongs to '{other}'"))
    allowed = UNITS_BY_CATEGORY.get(p.category, {"count"})
    if p.unit not in allowed:
        found.append(Finding("error", "unit", f"{p.category} is sold by {' or '.join(allowed)}"))

    volume_l = p.case_length_cm * p.case_width_cm * p.case_height_cm / 1000
    density = p.unit_weight_kg * p.case_pack / volume_l
    typical = DENSITY_KG_PER_L[p.category]
    if density > 3 * typical and density / 2.54**3 < 3 * typical:
        found.append(Finding("warning", "case dimensions",
                             f"a full case would weigh {density:.1f} kg per liter: these "
                             f"dimensions look like inches, not cm (× 2.54 = "
                             f"{p.case_length_cm * 2.54:.0f} × {p.case_width_cm * 2.54:.0f} × "
                             f"{p.case_height_cm * 2.54:.0f} cm)"))
    elif not typical / 4 < density < 4 * typical:
        found.append(Finding("warning", "case dimensions",
                             f"a full case would weigh {density:.2f} kg per liter; typical for "
                             f"{p.category} is about {typical} (fields swapped?)"))

    match = process.extractOne(p.name, catalog.name, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= 80:
        pid = catalog.id[match[2]]
        found.append(Finding("warning", "name", f"possible duplicate of '{match[0]}' "
                             f"(product {pid}, {match[1]:.0f} % similar)"))
    return found
