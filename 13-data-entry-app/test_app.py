from streamlit.testing.v1 import AppTest

from inventory_data.master import gtin13


def run(tmp_path, monkeypatch, **fields) -> AppTest:
    monkeypatch.setenv("ENTRIES_PATH", str(tmp_path / "entries.csv"))
    at = AppTest.from_file("app.py", default_timeout=30).run()
    for key, value in fields.items():
        widget = at.text_input(key=key) if key in ("name", "gtin") else (
            at.selectbox(key=key) if key in ("category", "unit", "supplier") else
            at.number_input(key=key))
        widget.set_value(value)
    return at.run()


GOOD = {"name": "Plantain", "gtin": gtin13(201, 161), "category": "produce", "unit": "kg",
        "supplier": 201, "length": 50.0, "width": 33.0, "height": 27.0, "pack": 18,
        "weight": 1.0}


def messages(at: AppTest) -> str:
    return " ".join(m.value for m in list(at.error) + list(at.warning) + list(at.success))


def test_good_product_passes(tmp_path, monkeypatch):
    at = run(tmp_path, monkeypatch, **GOOD)
    assert "All checks pass" in messages(at)
    at.button(key="save").click().run()
    assert (tmp_path / "entries.csv").read_text().count("accepted") == 1


def test_dimensions_in_inches_are_flagged(tmp_path, monkeypatch):
    at = run(tmp_path, monkeypatch, **GOOD | {"length": 19.9, "width": 13.0, "height": 10.6})
    assert "look like inches" in messages(at)


def test_schema_errors_block_saving(tmp_path, monkeypatch):
    at = run(tmp_path, monkeypatch, **GOOD | {"gtin": "702010001618", "unit": "liter"})
    assert "gtin" in messages(at)
    assert at.button(key="save").disabled


def test_duplicate_is_flagged(tmp_path, monkeypatch):
    at = run(tmp_path, monkeypatch, **GOOD | {"name": "Bananas Organic"})
    assert "possible duplicate of 'Organic Banana'" in messages(at)
