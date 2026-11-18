#!/usr/bin/env python
# coding: utf-8
"""
Offline test for the GUI's data-processing logic.

This does NOT require a database connection — it exercises the number parsing,
category filtering, column sorting, and metrics computation against the sample
data found in `output_format_example.json`.

Run:
    python test_gui_logic.py
"""

import json
import os

import gui


def load_sample_rows():
    """Load output_format_example.json and reshape it to DB-style dicts."""
    path = os.path.join(os.path.dirname(__file__), "output_format_example.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    rows = []
    for item in raw:
        rows.append({
            "id": item.get("properties.id", ""),
            "rua": item.get("properties.rua", ""),
            "preco": item.get("properties.preco", ""),
            "url": item.get("properties.url", ""),
            "bairro": item.get("properties.regiao", ""),
            "areaEmM2": item.get("properties.areaEmM2", ""),
            "n_dormitorios": item.get("properties.n_dormitorios", ""),
            "n_banheiros": item.get("properties.n_banheiros", ""),
            "n_garagem": item.get("properties.n_garagem", ""),
            "resumo": item.get("properties.resumo", ""),
            "condominio": "",
            "iptu": "",
        })
    return rows


def check(name, cond, extra=""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  ({extra})" if extra else ""))
    if not cond:
        failures.append(name)


failures = []


def main():
    rows = load_sample_rows()
    print(f"Loaded {len(rows)} sample rows\n")

    # --- parsing sanity ------------------------------------------------------
    check("price parse R$ 2.800.000",
          gui.parse_number("R$ 2.800.000") == 2800000.0)
    check("price parse 273 - 330 -> mid",
          abs(gui.parse_number("273 - 330") - 301.5) < 1e-9)
    check("bedrooms range 3 - 4",
          gui.parse_int("3 - 4") == 4)  # mid=3.5 -> 4
    check("bathrooms range 6 - 7",
          gui.parse_int("6 - 7") == 7)  # mid=6.5 -> 7
    check("garage 3 - 4",
          gui.parse_int("3 - 4") == 4)
    check("non-numeric -> None",
          gui.parse_number("Valor sob consulta") is None)
    check("empty -> None",
          gui.parse_number("") is None)
    check("None -> None",
          gui.parse_number(None) is None)

    # --- category filtering --------------------------------------------------
    all_rows = gui.filter_category(rows, "all")
    check("all keeps every row", len(all_rows) == len(rows))

    cheapest = gui.filter_category(rows, "cheapest")
    if cheapest:
        first_price = gui._price_of(cheapest[0])
        last_price = gui._price_of(cheapest[-1])
        check("cheapest sorted ascending",
              first_price <= last_price,
              f"first={first_price}, last={last_price}")
        check("cheapest first is R$ 213.000",
              first_price == 213000.0, f"got {first_price}")

    expensive = gui.filter_category(rows, "expensive")
    if expensive:
        first_price = gui._price_of(expensive[0])
        last_price = gui._price_of(expensive[-1])
        check("expensive sorted descending", first_price >= last_price)

    largest = gui.filter_category(rows, "largest")
    if largest:
        first_area = gui._area_of(largest[0])
        # The "largest" category must return the row with the greatest area.
        max_area_all = max(gui._area_of(r) for r in rows if gui._area_of(r) is not None)
        check("largest has the biggest area", first_area == max_area_all,
              f"got {first_area}, expected {max_area_all}")

    value = gui.filter_category(rows, "value")
    if value:
        ppm = [gui._usable_price(r) for r in value]
        check("best-value sorted by ppm ascending",
              all(ppm[i] <= ppm[i + 1] for i in range(len(ppm) - 1)))

    # --- column sorting -------------------------------------------------------
    by_id = gui.sort_rows(rows, "id")
    check("sort by id ascending", [r["id"] for r in by_id] ==
          sorted((r["id"] for r in rows), key=int))
    check("sort by id descending", [r["id"] for r in gui.sort_rows(rows, "id", False)] ==
          list(reversed([r["id"] for r in by_id])))

    by_price = gui.sort_rows(rows, "preco")
    prices = [gui.parse_number(r["preco"]) for r in by_price]
    usable_prices = [p for p in prices if p is not None]
    check("numeric sort by price ascending", usable_prices == sorted(usable_prices))
    check("missing prices go last", prices[:len(usable_prices)] == usable_prices)

    by_area_desc = gui.sort_rows(rows, "areaEmM2", False)
    areas = [gui.parse_number(r["areaEmM2"]) for r in by_area_desc]
    usable_areas = [a for a in areas if a is not None]
    check("numeric sort by area descending", usable_areas == sorted(usable_areas, reverse=True))

    text_rows = [
        {"bairro": "Água Santa"},
        {"bairro": "centro"},
        {"bairro": "Moinhos de Vento"},
        {"bairro": "Cristal"},
        {"bairro": ""},
    ]
    by_bairro = gui.sort_rows(text_rows, "bairro")
    check("text sort ignores case and accents",
          [r["bairro"] for r in by_bairro] ==
          ["Água Santa", "centro", "Cristal", "Moinhos de Vento", ""])
    check("text sort descending",
          [r["bairro"] for r in gui.sort_rows(text_rows, "bairro", False)] ==
          ["Moinhos de Vento", "Cristal", "centro", "Água Santa", ""])

    # --- metrics ---------------------------------------------------------------
    m = gui.compute_metrics(all_rows)
    check("metrics count matches", m["count"] == len(rows))
    check("metrics avg_area present", m["avg_area"] is not None)
    check("metrics avg_price present", m["avg_price"] is not None)
    check("metrics avg_ppm present", m["avg_ppm"] is not None)
    check("metrics avg_room present", m["avg_room"] is not None)
    check("metrics avg_bath present", m["avg_bath"] is not None)
    check("metrics avg_garage present", m["avg_garage"] is not None)

    print("\nMetrics (All listings):")
    for k, v in m.items():
        print(f"  {k}: {v}")

    # --- formatters -------------------------------------------------------------
    check("format_brl", gui.format_brl(2800000.0) == "R$ 2.800.000",
          gui.format_brl(2800000.0))
    check("format_brl none", gui.format_brl(None) == "—")
    check("format_num", gui.format_num(105.5) == "105,5",
          gui.format_num(105.5))

    print(f"\n{'='*40}\n{'ALL TESTS PASSED' if not failures else f'{len(failures)} FAILURE(S)'}\n{'='*40}")


if __name__ == "__main__":
    main()
    if failures:
        raise SystemExit(1)