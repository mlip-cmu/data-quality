"""Enter a new product. Live data quality feedback, as the paper's 'real-time indicators'."""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import inventory_data as d
from checks import check

ENTRIES = Path(os.environ.get("ENTRIES_PATH", "out/entries.csv"))
STAFF = ["E011 · Ana (store 1)", "E012 · Ben (store 1)", "E021 · Chloe (store 2)",
         "E031 · Dev (store 3)"]


@st.cache_data
def reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    return d.products(), d.suppliers()


catalog, suppliers = reference()
st.set_page_config(page_title="New product", page_icon="🧺", layout="wide")
staff = st.sidebar.selectbox("Entered by", STAFF, key="staff")
entry, scorecard = st.tabs(["New product", "Data quality scorecard"])

with entry:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("New product")
        name = st.text_input("Product name", key="name")
        gtin = st.text_input("GTIN (13 digits)", key="gtin")
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Category", sorted(catalog.category.unique()), key="category")
        unit = c2.selectbox("Sold by", ["count", "kg", "liter"], key="unit")
        price = c3.number_input("Price per unit ($)", min_value=0.0, value=1.99, step=0.1,
                                key="price")
        supplier = st.selectbox("Supplier", suppliers.id, key="supplier",
                                format_func=lambda i: f"{i} · {suppliers.set_index('id').name[i]}")
        c4, c5, c6 = st.columns(3)
        length = c4.number_input("Case length (cm)", min_value=0.0, value=40.0, key="length")
        width = c5.number_input("Case width (cm)", min_value=0.0, value=30.0, key="width")
        height = c6.number_input("Case height (cm)", min_value=0.0, value=20.0, key="height")
        c7, c8, c9 = st.columns(3)
        pack = c7.number_input("Units per case", min_value=0, value=12, key="pack")
        weight = c8.number_input("Weight per unit (kg)", min_value=0.0, value=0.5, key="weight")
        shelf = c9.number_input("Shelf life (days)", min_value=0, value=14, key="shelf")

    values = {"name": name, "gtin": gtin.strip(), "category": category, "unit": unit,
              "unit_price": price, "supplier_id": int(supplier), "case_pack": int(pack),
              "case_length_cm": length, "case_width_cm": width, "case_height_cm": height,
              "unit_weight_kg": weight, "shelf_life_days": int(shelf)}
    findings = check(values, catalog)
    errors = [f for f in findings if f.level == "error"]

    with right:
        st.subheader("Data quality check")
        if not findings:
            st.success("All checks pass.", icon="✅")
        for f in findings:
            show = st.error if f.level == "error" else st.warning
            show(f"**{f.field}**: {f.message}", icon="⛔" if f.level == "error" else "⚠️")
        status = "needs review" if findings else "accepted"
        if st.button("Save", type="primary", disabled=bool(errors), key="save"):
            ENTRIES.parent.mkdir(parents=True, exist_ok=True)
            row = pd.DataFrame([values | {
                "entered_by": staff, "entered_at": datetime.now().isoformat(timespec="seconds"),
                "status": status, "warnings": "; ".join(f.message for f in findings)}])
            row.to_csv(ENTRIES, mode="a", header=not ENTRIES.exists(), index=False)
            st.toast(f"Saved: {status}")
        if errors:
            st.caption("Fix the errors to save. Warnings can be saved; a data steward reviews them.")

with scorecard:
    st.subheader("Data quality of the entries per person")
    if ENTRIES.exists():
        e = pd.read_csv(ENTRIES)
        card = e.groupby("entered_by").status.value_counts().unstack(fill_value=0)
        card["accepted without review"] = card.get("accepted", 0) / card.sum(axis=1)
        st.dataframe(card.style.format({"accepted without review": "{:.0%}"}))
        st.caption("Visible data work: the entries each person made and how many needed a review.")
    else:
        st.info("No entries yet.")
