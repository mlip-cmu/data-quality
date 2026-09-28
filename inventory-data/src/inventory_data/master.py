"""Master data of a fictional supermarket chain: suppliers, products, stores."""

import math

import pandas as pd

SUPPLIERS = [
    (201, "Fresh Fields Produce", "Maria Lopez", "412-555-0101", 1),
    (202, "Keystone Dairy", "Tom Becker", "717-555-0102", 1),
    (203, "Allegheny Bakery", "Ann Novak", "412-555-0103", 1),
    (204, "Laurel Highlands Meats", "Raj Patel", "724-555-0104", 2),
    (205, "Great Lakes Seafood", "Lena Fischer", "216-555-0105", 2),
    (206, "Three Rivers Beverages", "Sam Carter", "412-555-0106", 3),
    (207, "Heartland Pantry", "Joy Kim", "614-555-0107", 3),
    (208, "Sunrise Frozen Foods", "Omar Haddad", "330-555-0108", 3),
    (209, "CleanHome Supplies", "Eve Walsh", "814-555-0109", 3),
    (210, "EcoRefill Co.", "Noah Green", "412-555-0110", 2),
    (211, "Ohio Valley Farms", "Ruth Miller", "740-555-0111", 1),
    (212, "Blue Ridge Grocery Supply", "Ken Ito", "540-555-0112", 2),
]

# id, name, category, unit, unit_price, supplier_id, base_demand (unit/day/store),
# shelf_life_days, unit_weight_kg, case_pack, family, size
PRODUCTS = [
    (101, "Banana", "produce", "kg", 1.49, 201, 25, 7, 1.0, 18, None, None),
    (102, "Cucumber", "produce", "count", 0.79, 211, 30, 10, 0.3, 24, None, None),
    (103, "Cauliflower", "produce", "count", 2.99, 211, 12, 10, 0.6, 12, None, None),
    (104, "Organic Banana", "produce", "kg", 1.99, 201, 8, 7, 1.0, 18, None, None),
    (105, "Gala Apple", "produce", "kg", 3.49, 211, 15, 30, 1.0, 18, None, None),
    (106, "Tomato", "produce", "kg", 3.99, 201, 12, 7, 1.0, 10, None, None),
    (107, "Iceberg Lettuce", "produce", "count", 1.89, 211, 14, 7, 0.7, 24, None, None),
    (108, "Avocado", "produce", "count", 1.25, 201, 20, 5, 0.2, 48, None, None),
    (109, "Carrots 2 lb Bag", "produce", "count", 1.99, 211, 10, 21, 0.9, 20, None, None),
    (110, "Potato", "produce", "kg", 1.29, 211, 18, 45, 1.0, 20, None, None),
    (111, "Yellow Onion", "produce", "kg", 1.59, 211, 10, 45, 1.0, 20, None, None),
    (112, "Strawberries 1 lb", "produce", "count", 3.99, 201, 15, 5, 0.45, 8, None, None),
    (113, "Lemon", "produce", "count", 0.69, 201, 12, 21, 0.1, 100, None, None),
    (114, "Watermelon", "produce", "count", 5.99, 201, 5, 14, 7.0, 4, None, None),
    (115, "Blueberries 6 oz", "produce", "count", 3.49, 201, 10, 7, 0.17, 12, None, None),
    (116, "Whole Milk 1/2 gal", "dairy", "count", 2.49, 202, 20, 14, 1.9, 9, "whole milk", 0.5),
    (117, "Whole Milk 1 gal", "dairy", "count", 3.79, 202, 25, 14, 3.9, 4, "whole milk", 1.0),
    (118, "Large Eggs 12 ct", "dairy", "count", 3.29, 202, 22, 30, 0.7, 15, None, None),
    (119, "Greek Yogurt 32 oz", "dairy", "count", 5.49, 202, 8, 21, 0.9, 6, None, None),
    (120, "Cheddar Cheese 8 oz", "dairy", "count", 3.99, 202, 10, 60, 0.23, 12, None, None),
    (121, "Salted Butter 1 lb", "dairy", "count", 4.99, 202, 8, 90, 0.45, 18, None, None),
    (122, "Orange Juice 52 oz", "beverages", "count", 4.29, 206, 10, 21, 1.6, 8, None, None),
    (123, "White Bread", "bakery", "count", 2.99, 203, 18, 5, 0.6, 12, None, None),
    (124, "Whole Wheat Bread", "bakery", "count", 3.49, 203, 12, 5, 0.6, 12, None, None),
    (125, "Bagels 6 ct", "bakery", "count", 3.99, 203, 8, 5, 0.5, 12, None, None),
    (126, "Croissant", "bakery", "count", 1.29, 203, 15, 3, 0.07, 24, None, None),
    (127, "Chicken Breast", "meat", "kg", 8.99, 204, 12, 4, 1.0, 10, None, None),
    (128, "Ground Beef", "meat", "kg", 10.99, 204, 10, 3, 1.0, 10, None, None),
    (129, "Pork Chops", "meat", "kg", 9.49, 204, 5, 4, 1.0, 10, None, None),
    (130, "Atlantic Salmon", "seafood", "kg", 21.99, 205, 4, 3, 1.0, 5, None, None),
    (131, "Frozen Shrimp 1 lb", "frozen", "count", 9.99, 205, 5, 180, 0.45, 12, None, None),
    (132, "Sparkling Water 12 pk", "beverages", "count", 5.99, 206, 12, 365, 4.5, 2, None, None),
    (133, "Cola 6 pk", "beverages", "count", 3.99, 206, 15, 270, 2.3, 4, "cola cans", 6),
    (134, "Cola 12 pk", "beverages", "count", 6.99, 206, 10, 270, 4.6, 2, "cola cans", 12),
    (135, "Bottled Water 24 pk", "beverages", "count", 4.99, 206, 14, 365, 12.5, 1, None, None),
    (136, "Ground Coffee 12 oz", "pantry", "count", 8.99, 207, 7, 180, 0.34, 6, None, None),
    (137, "Iced Tea 1 gal", "beverages", "count", 3.29, 206, 6, 120, 3.9, 4, None, None),
    (138, "Spaghetti 1 lb", "pantry", "count", 1.49, 207, 12, 730, 0.45, 20, None, None),
    (139, "Marinara Sauce 24 oz", "pantry", "count", 2.99, 207, 8, 540, 0.8, 12, None, None),
    (140, "Long Grain Rice 2 lb", "pantry", "count", 2.79, 207, 7, 730, 0.9, 12, "rice", 2),
    (141, "Long Grain Rice 5 lb", "pantry", "count", 5.99, 207, 4, 730, 2.3, 8, "rice", 5),
    (142, "Peanut Butter 16 oz", "pantry", "count", 3.49, 207, 7, 365, 0.45, 12, None, None),
    (143, "Tomato Soup", "pantry", "count", 1.19, 207, 10, 730, 0.3, 24, None, None),
    (144, "Corn Flakes 18 oz", "pantry", "count", 4.29, 207, 7, 365, 0.5, 12, None, None),
    (145, "Olive Oil 1 L", "pantry", "count", 9.99, 207, 4, 540, 0.95, 12, None, None),
    (146, "Vanilla Ice Cream 1.5 qt", "frozen", "count", 4.99, 208, 8, 365, 1.3, 6, None, None),
    (147, "Frozen Pizza", "frozen", "count", 5.99, 208, 9, 270, 0.6, 10, None, None),
    (148, "Frozen Peas 16 oz", "frozen", "count", 1.99, 208, 5, 365, 0.45, 12, None, None),
    (149, "Ice Cubes 7 lb", "frozen", "count", 2.99, 208, 4, 365, 3.2, 6, None, None),
    (150, "Paper Towels 6 rolls", "household", "count", 8.99, 209, 7, 1825, 1.2, 4, None, None),
    (151, "Toilet Paper 12 rolls", "household", "count", 9.99, 209, 9, 1825, 1.5, 4, None, None),
    (152, "Dish Soap 20 oz", "household", "count", 2.99, 209, 5, 1095, 0.65, 12, None, None),
    (153, "Laundry Detergent 100 oz", "household", "count", 12.99, 209, 4, 1095, 3.2, 4, None, None),
    (154, "Refill Laundry Detergent", "refill", "liter", 3.99, 210, 6, 365, 1.05, 20, None, None),
    (155, "Refill Dish Soap", "refill", "liter", 3.49, 210, 3, 365, 1.03, 20, None, None),
    (156, "Refill Olive Oil", "refill", "liter", 11.99, 210, 2, 540, 0.92, 10, None, None),
    (157, "Refill Oat Milk", "refill", "liter", 2.99, 210, 4, 10, 1.03, 20, None, None),
    (158, "Fresh Basil", "produce", "count", 2.49, 211, 5, 5, 0.03, 12, None, None),
    (159, "Sliced Deli Turkey", "meat", "kg", 12.99, 204, 4, 7, 1.0, 5, None, None),
    (160, "Hummus 10 oz", "dairy", "count", 3.99, 212, 6, 30, 0.28, 12, None, None),
]

# Change of demand per degree Celsius above 15 °C (relative).
TEMP_SENSITIVITY = {114: 0.04, 132: 0.02, 135: 0.025, 137: 0.035, 146: 0.035, 149: 0.06,
                    143: -0.015, 112: 0.015, 106: 0.01}
# Seasonal amplitude and peak day of year.
SEASON = {"produce": (0.10, 200), "beverages": (0.10, 200), "frozen": (0.05, 200),
          "bakery": (0.05, 350), "pantry": (0.05, 20), "meat": (0.08, 190)}
SEASON_OVERRIDE = {114: (0.9, 205), 143: (0.3, 20), 146: (0.3, 200), 103: (0.25, 20)}
DENSITY_KG_PER_L = {"produce": 0.45, "dairy": 0.9, "bakery": 0.25, "meat": 0.8, "seafood": 0.8,
                    "frozen": 0.6, "beverages": 0.9, "pantry": 0.6, "household": 0.3,
                    "refill": 1.0}

# id, name, city, state, zip, region, size_sqm, opened, weather_station
STORES = [
    (1, "Oakland", "Pittsburgh", "PA", "15213", "Pittsburgh", 2400, "2010-05-01", "PIT"),
    (2, "Squirrel Hill", "Pittsburgh", "PA", "15217", "Pittsburgh", 2100, "2012-03-15", "PIT"),
    (3, "Downtown", "Pittsburgh", "PA", "15222", "Pittsburgh", 1500, "2016-09-01", "PIT"),
    (4, "Cranberry", "Cranberry Township", "PA", "16066", "Pittsburgh", 3200, "2014-06-01", "PIT"),
    (5, "Monroeville", "Monroeville", "PA", "15146", "Pittsburgh", 2800, "2011-11-01", "PIT"),
    (6, "Erie Bayfront", "Erie", "PA", "16501", "Northwest PA", 2200, "2018-04-01", "ERI"),
    (7, "Harrisburg", "Harrisburg", "PA", "17101", "Central PA", 2500, "2019-10-01", "MDT"),
    (8, "Cleveland Flats", "Cleveland", "OH", "44113", "Ohio", 2600, "2021-02-01", "CLE"),
    (9, "Tampa Heights", "Tampa", "FL", "33602", "Florida", 2300, "2025-06-01", "TPA"),
    (10, "Orlando Lake Eola", "Orlando", "FL", "32801", "Florida", 2000, "2025-06-01", "MCO"),
]
NEW_STORES = {9, 10}

ZIP_CODES = [
    ("15213", "Pittsburgh", "PA"), ("15217", "Pittsburgh", "PA"), ("15222", "Pittsburgh", "PA"),
    ("15232", "Pittsburgh", "PA"), ("16066", "Cranberry Township", "PA"),
    ("15146", "Monroeville", "PA"), ("16501", "Erie", "PA"), ("17101", "Harrisburg", "PA"),
    ("44113", "Cleveland", "OH"), ("43215", "Columbus", "OH"), ("33602", "Tampa", "FL"),
    ("32801", "Orlando", "FL"),
]

# station: mean annual temperature, seasonal amplitude (°C)
WEATHER_STATIONS = {"PIT": (11.0, 12.0), "ERI": (10.0, 12.0), "MDT": (12.5, 12.0),
                    "CLE": (10.5, 12.5), "TPA": (23.5, 5.5), "MCO": (22.5, 5.5)}

UNITS = ["count", "kg", "liter"]
CATEGORIES = sorted(DENSITY_KG_PER_L)


def gtin13(supplier_id: int, product_id: int) -> str:
    body = f"07{supplier_id:04d}{product_id:06d}"
    return body + str(gtin_check_digit(body))


def gtin_check_digit(body12: str) -> int:
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body12))
    return (10 - total % 10) % 10


def gtin_is_valid(gtin: str) -> bool:
    gtin = str(gtin)
    return len(gtin) == 13 and gtin.isdigit() and gtin_check_digit(gtin[:12]) == int(gtin[12])


def _case_dims_cm(unit_weight_kg: float, case_pack: int, category: str) -> tuple[float, ...]:
    volume_l = unit_weight_kg * case_pack / DENSITY_KG_PER_L[category] * 1.15
    side = (volume_l * 1000 / (1.5 * 1.0 * 0.8)) ** (1 / 3)
    return tuple(round(side * r * 2) / 2 for r in (1.5, 1.0, 0.8))


def suppliers() -> pd.DataFrame:
    cols = ["id", "name", "contact_name", "contact_phone", "lead_time_days"]
    return pd.DataFrame(SUPPLIERS, columns=cols)


def products() -> pd.DataFrame:
    cols = ["id", "name", "category", "unit", "unit_price", "supplier_id", "base_demand",
            "shelf_life_days", "unit_weight_kg", "case_pack", "family", "size"]
    df = pd.DataFrame(PRODUCTS, columns=cols)
    df.insert(1, "gtin", [gtin13(s, i) for s, i in zip(df.supplier_id, df.id, strict=True)])
    dims = [_case_dims_cm(w, c, cat) for w, c, cat in
            zip(df.unit_weight_kg, df.case_pack, df.category, strict=True)]
    df["case_length_cm"], df["case_width_cm"], df["case_height_cm"] = zip(*dims, strict=True)
    return df


def stores(include_new: bool = True) -> pd.DataFrame:
    cols = ["id", "name", "city", "state", "zip", "region", "size_sqm", "opened", "station"]
    df = pd.DataFrame(STORES, columns=cols)
    df["opened"] = pd.to_datetime(df["opened"])
    return df if include_new else df[~df.id.isin(NEW_STORES)].reset_index(drop=True)


def zip_codes() -> pd.DataFrame:
    return pd.DataFrame(ZIP_CODES, columns=["zip", "city", "state"])


def case_volume_l(df: pd.DataFrame) -> pd.Series:
    return df.case_length_cm * df.case_width_cm * df.case_height_cm / 1000


def shelf_volume_l(products_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    """Planogram: shelf space per store and product, sized for ~4 days of demand."""
    rows = []
    for s in stores_df.itertuples():
        scale = s.size_sqm / 2400
        for p in products_df.itertuples():
            cases = max(2, math.ceil(4 * p.base_demand * scale / p.case_pack))
            vol = p.case_length_cm * p.case_width_cm * p.case_height_cm / 1000
            rows.append((s.id, p.id, round(cases * vol, 1)))
    return pd.DataFrame(rows, columns=["store_id", "product_id", "shelf_volume_l"])
