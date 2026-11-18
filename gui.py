#!/usr/bin/env python
# coding: utf-8
"""
Zap Scraper GUI
===============

A desktop dashboard for the records stored by `zap.py` in the MySQL database.

Features
--------
* Connect to the local MySQL database and pick any scraped table.
* Browse all listings or view "recommended" categories:
    - All listings
    - Best value (lowest price per m²)
    - Largest apartments (by area)
    - Most rooms (bedrooms)
    - Cheapest listings
    - Most garages / parking
    - Most expensive / luxury
* Live metrics panel for the selected category:
    average m², average price, average bedrooms, average bathrooms,
    average garages, average condo fee, average IPTU, counts, min/max.
* Sort the results by clicking any column header (click again to reverse).
* Open a listing URL directly in your web browser.

Run:
    python gui.py
"""

import re
import unicodedata
import webbrowser

import tkinter as tk
from tkinter import ttk, messagebox

# pymysql is imported lazily inside Database.connect() so that the pure data
# logic in this module (parsing, filtering, metrics) can be unit-tested without
# the MySQL driver installed. The GUI itself requires pymysql.
import db_config


# ---------------------------------------------------------------------------
# Numeric helpers ------------------------------------------------------------
# ---------------------------------------------------------------------------

def parse_number(text, method="mid"):
    """
    Extract a usable number from the messy TEXT columns of the scraper.

    Examples:
        "R$ 2.800.000"   -> 2800000
        "205"            -> 205
        "273 - 330"      -> 301.5 (mid), 273 (min), 330 (max)
        "6 - 7"          -> 6.5 (mid)
        "" or "Valor sob consulta" -> None

    method: "mid" (average of a range), "min", or "max".
    """
    if text is None:
        return None

    # Collect all standalone numeric tokens (whole numbers, may have dots as
    # thousand separators and commas as decimal separators, Brazilian style).
    # - First alternative matches grouped numbers like "2.800.000" or "1.234,56".
    # - Second alternative matches plain runs like "2700", "105", or "3".
    matches = re.findall(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?", str(text))
    if not matches:
        return None

    values = []
    for m in matches:
        # Brazilian/European numeric format: "2.800.000" or "1.234,56"
        if "," in m and "." in m:
            cleaned = m.replace(".", "").replace(",", ".")
        elif "," in m:
            cleaned = m.replace(",", ".")
        else:
            cleaned = m.replace(".", "")

        try:
            values.append(float(cleaned))
        except ValueError:
            continue

    if not values:
        return None

    if method == "min":
        return min(values)
    if method == "max":
        return max(values)
    # "mid" -> average of the min and max (good for ranges like "273 - 330")
    return (min(values) + max(values)) / 2.0


def parse_int(text, method="mid"):
    """Like parse_number but returns an int (rounded half-up) or None."""
    n = parse_number(text, method=method)
    if n is None:
        return None
    # Round half-up (not Python's half-to-even), which is the expected
    # behaviour for counts like "6 - 7" -> 7 and "3 - 4" -> 4.
    return int(n + 0.5)


# ---------------------------------------------------------------------------
# Category definitions -------------------------------------------------------
# ---------------------------------------------------------------------------

# Each category is a callable that receives the full list of rows (as dicts)
# and returns an ordered list of rows. If the SQL could do it directly we do it
# in SQL, otherwise we sort/filter in Python for robustness on messy data.
CATEGORIES = {
    "All listings": "all",
    "Best value (price/m²)": "value",
    "Largest apartments": "largest",
    "Most rooms (bedrooms)": "rooms",
    "Cheapest listings": "cheapest",
    "Most garages / parking": "garage",
    "Most expensive / luxury": "expensive",
}


def _coerce_to_int(value):
    """Turn a row value into an int (matters for columns stored as TEXT)."""
    n = parse_int(value, method="mid")
    return n if n is not None else 0


def _price_of(row):
    return parse_number(row.get("preco"), method="mid")


def _area_of(row):
    return parse_number(row.get("areaEmM2"), method="mid")


def _room_of(row):
    return parse_int(row.get("n_dormitorios"), method="mid") or 0


def _bath_of(row):
    return parse_int(row.get("n_banheiros"), method="mid") or 0


def _garage_of(row):
    return parse_int(row.get("n_garagem"), method="mid") or 0


def _usable_price(row):
    """
    A listing is only "usable" for value comparisons when it has both a real
    price and a real area.
    """
    p = _price_of(row)
    a = _area_of(row)
    if p is None or not p or a is None or not a:
        return None
    return p / a


def filter_category(rows, category_key):
    """Return the ordered list of rows for a given category key."""
    # Copy so callers never mutate the original list.
    rows = list(rows)

    if category_key == "all":
        return rows

    if category_key == "value":
        usable = [r for r in rows if _usable_price(r) is not None]
        usable.sort(key=_usable_price)
        return usable

    if category_key == "largest":
        usable = [r for r in rows if _area_of(r) is not None]
        usable.sort(key=_area_of, reverse=True)
        return usable

    if category_key == "rooms":
        usable = [r for r in rows if _room_of(r) > 0]
        usable.sort(key=_room_of, reverse=True)
        return usable

    if category_key == "cheapest":
        usable = [r for r in rows if _price_of(r) is not None]
        usable.sort(key=_price_of)
        return usable

    if category_key == "garage":
        usable = [r for r in rows if _garage_of(r) > 0]
        usable.sort(key=_garage_of, reverse=True)
        return usable

    if category_key == "expensive":
        usable = [r for r in rows if _price_of(r) is not None]
        usable.sort(key=_price_of, reverse=True)
        return usable

    return rows


# ---------------------------------------------------------------------------
# Column sorting -------------------------------------------------------------
# ---------------------------------------------------------------------------

# These columns contain numbers stored as TEXT, so they must be sorted by their
# parsed value (e.g. 2.800.000 > 213.000), not as plain strings.
NUMERIC_COLUMNS = {
    "id", "preco", "areaEmM2", "n_dormitorios", "n_banheiros",
    "n_garagem", "condominio", "iptu",
}


def _text_sort_key(value):
    """Case/accent-insensitive key so 'Área' sorts next to 'area'."""
    text = str(value).strip()
    if not text:
        return None
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def sort_rows(rows, column, ascending=True):
    """
    Return a new list of rows sorted by a display column.

    Numeric columns are compared by parsed value; all other columns are
    compared as case/accent-insensitive text. Rows with no usable value are
    always placed at the end, in either direction.
    """
    rows = list(rows)

    def key_for(row):
        value = row.get(column)
        if column in NUMERIC_COLUMNS:
            return parse_number(value, method="mid")
        return _text_sort_key(value) if value is not None else None

    valued = []
    missing = []
    for row in rows:
        key = key_for(row)
        if key is None:
            missing.append(row)
        else:
            valued.append((key, row))

    # Python's sort is stable, so rows with equal keys keep their original
    # order even when the direction is reversed.
    valued.sort(key=lambda pair: pair[0], reverse=not ascending)
    return [row for _, row in valued] + missing


# ---------------------------------------------------------------------------
# Metrics --------------------------------------------------------------------
# ---------------------------------------------------------------------------

def average(values):
    """Return a float average of a list of non-None numbers, or None."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def compute_metrics(rows):
    """
    Compute aggregate metrics over a list of row dicts.

    Prices are BRL; areas in m²; counts are unitless.
    """
    prices = [_price_of(r) for r in rows]
    areas = [_area_of(r) for r in rows]
    rooms = [_room_of(r) for r in rows]
    baths = [_bath_of(r) for r in rows]
    garages = [_garage_of(r) for r in rows]
    condos = [parse_number(r.get("condominio"), method="mid") for r in rows]
    iptus = [parse_number(r.get("iptu"), method="mid") for r in rows]

    # Drop unparseable (None) values before computing stats.
    clean_prices = [p for p in prices if p is not None]
    clean_areas = [a for a in areas if a is not None]

    avg_price = average(prices)
    avg_area = average(areas)
    avg_room = average(rooms)
    avg_bath = average(baths)
    avg_garage = average(garages)
    avg_condo = average(condos)
    avg_iptu = average(iptus)

    # price per m²: only pairs with both values
    ppm = []
    for r in rows:
        u = _usable_price(r)
        if u is not None:
            ppm.append(u)

    return {
        "count": len(rows),
        "with_price": len(clean_prices),
        "avg_price": avg_price,
        "avg_area": avg_area,
        "avg_room": avg_room,
        "avg_bath": avg_bath,
        "avg_garage": avg_garage,
        "avg_condo": avg_condo,
        "avg_iptu": avg_iptu,
        "avg_ppm": average(ppm),
        "min_price": min(clean_prices) if clean_prices else None,
        "max_price": max(clean_prices) if clean_prices else None,
        "min_area": min(clean_areas) if clean_areas else None,
        "max_area": max(clean_areas) if clean_areas else None,
    }


def format_brl(value, decimals=0):
    """Format a number as BRL currency: R$ 1.234.567."""
    if value is None:
        return "—"
    return "R$ {:,.{}f}".format(value, decimals).replace(",", "X").replace(".", ",").replace("X", ".")


def format_num(value, decimals=1):
    if value is None:
        return "—"
    if decimals == 0:
        return "{:,.0f}".format(value).replace(",", ".")
    return "{:,.{}f}".format(value, decimals).replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Database layer -------------------------------------------------------------
# ---------------------------------------------------------------------------

class Database:
    def __init__(self):
        self.conn = None
        self.params = db_config.get_db_params()

    def connect(self):
        """Connect to MySQL; raises an exception on failure."""
        import pymysql
        from pymysql.cursors import DictCursor

        self.close()
        self.conn = pymysql.connect(**self.params, cursorclass=DictCursor)
        return self.conn

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def is_connected(self):
        return self.conn is not None

    def list_tables(self):
        """Return a list of table names in the connected database."""
        with self.conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            return [list(row.values())[0] for row in cur.fetchall()]

    def fetch_all(self, table):
        """Return all rows (dicts) from a table."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{table}`")
            return cur.fetchall()


# ---------------------------------------------------------------------------
# GUI ------------------------------------------------------------------------
# ---------------------------------------------------------------------------

# Columns to show, and their human-readable headers.
COLUMNS = [
    ("id", "ID"),
    ("bairro", "Bairro"),
    ("rua", "Rua"),
    ("preco", "Preço"),
    ("areaEmM2", "Área (m²)"),
    ("n_dormitorios", "Dorm."),
    ("n_banheiros", "Banh."),
    ("n_garagem", "Garagem"),
    ("condominio", "Condomínio"),
    ("iptu", "IPTU"),
    ("url", "Link"),
]


class ZapGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zap Scraper — Apartment Dashboard")
        self.root.geometry("1200x720")
        self.root.minsize(1000, 620)

        self.db = Database()
        self.rows = []            # all rows for the current table
        self.current_rows = []    # filtered/ordered rows for current category
        self.current_category = "all"
        self.sort_column = None   # display column currently used for sorting
        self.sort_ascending = True

        self._build_style()
        self._build_ui()

        # Try to connect on startup; if the DB is down, show a friendly banner.
        self.initial_connect()

    # ---- styling ------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#f4f6f9"
        card = "#ffffff"
        accent = "#2b6cb0"

        style.configure(".", background=bg, foreground="#1a202c", font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=card, relief="flat")
        style.configure("Sidebar.TFrame", background="#22303f")

        style.configure("Title.TLabel", background=bg, foreground="#1a202c",
                        font=("Segoe UI", 15, "bold"))
        style.configure("Section.TLabel", background=card, foreground="#2d3748",
                        font=("Segoe UI", 10, "bold"))
        style.configure("MetricValue.TLabel", background=card, foreground="#1a202c",
                        font=("Segoe UI", 13, "bold"))
        style.configure("MetricLabel.TLabel", background=card, foreground="#718096",
                        font=("Segoe UI", 9))

        style.configure("Category.TButton", background="#2b3a4d", foreground="#e2e8f0",
                        padding=(10, 8), anchor="w", font=("Segoe UI", 10))
        style.map("Category.TButton",
                  background=[("active", "#2b6cb0"), ("selected", "#2b6cb0")],
                  foreground=[("selected", "#ffffff")])

        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff",
                        foreground="#1a202c", rowheight=26)
        style.configure("Treeview.Heading", background="#e2e8f0", foreground="#1a202c",
                        font=("Segoe UI", 10, "bold"))

        self.accent = accent

    # ---- layout -------------------------------------------------------------
    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Left sidebar with categories
        self.sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", padding=12)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.sidebar.columnconfigure(0, weight=1)
        ttk.Label(self.sidebar, text="Categorias", style="Section.TLabel",
                  background="#22303f", foreground="#a0aec0",
                  font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.category_buttons = {}
        for i, (label, key) in enumerate(CATEGORIES.items(), start=1):
            btn = ttk.Button(self.sidebar, text=label, style="Category.TButton",
                             command=lambda k=key, l=label: self.select_category(k, l))
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self.category_buttons[key] = btn

        self.status_label = ttk.Label(self.sidebar, text="Desconectado",
                                      background="#22303f", foreground="#fc8181",
                                      font=("Segoe UI", 9))
        self.status_label.grid(row=len(CATEGORIES) + 2, column=0, sticky="ew", pady=(18, 4))
        self.count_label = ttk.Label(self.sidebar, text="",
                                     background="#22303f", foreground="#a0aec0",
                                     font=("Segoe UI", 9))
        self.count_label.grid(row=len(CATEGORIES) + 3, column=0, sticky="ew")

        # Main area
        self.main = ttk.Frame(self.root, padding=16)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(2, weight=1)

        # Header: title + connection controls
        header = ttk.Frame(self.main)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Apartamentos — Base de Dados Zap", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        controls = ttk.Frame(header)
        controls.grid(row=0, column=1, sticky="e")
        ttk.Label(controls, text="Tabela:").grid(row=0, column=0, padx=(0, 4))
        self.table_combo = ttk.Combobox(controls, width=28, state="readonly")
        self.table_combo.grid(row=0, column=1, padx=(0, 8))
        self.table_combo.bind("<<ComboboxSelected>>", lambda e: self.on_table_changed())
        self.refresh_btn = ttk.Button(controls, text="Atualizar", command=self.on_refresh)
        self.refresh_btn.grid(row=0, column=2)

        # Metrics cards
        metrics = ttk.Frame(self.main)
        metrics.grid(row=1, column=0, sticky="ew", pady=(16, 14))
        for c in range(6):
            metrics.columnconfigure(c, weight=1)

        self.metric_values = {}
        metrics_spec = [
            ("avg_ppm", "Preço médio p/ m²"),
            ("avg_price", "Preço médio"),
            ("avg_area", "Área média (m²)"),
            ("avg_room", "Média de quartos"),
            ("avg_bath", "Média de banheiros"),
            ("avg_garage", "Média de garagens"),
        ]
        for i, (key, label) in enumerate(metrics_spec):
            card = ttk.Frame(metrics, style="Card.TFrame", padding=10)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            card.columnconfigure(0, weight=1)
            ttk.Label(card, text=label, style="MetricLabel.TLabel").grid(row=0, column=0, sticky="w")
            value = ttk.Label(card, text="—", style="MetricValue.TLabel")
            value.grid(row=1, column=0, sticky="w")
            self.metric_values[key] = value

        # Records table
        table_frame = ttk.Frame(self.main, style="Card.TFrame", padding=8)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        self.table_title = ttk.Label(table_frame, text="Registros", style="Section.TLabel")
        self.table_title.grid(row=0, column=0, sticky="w", padx=4, pady=(2, 6))

        columns = [key for key, _ in COLUMNS]
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for key, head in COLUMNS:
            self.tree.heading(key, text=head,
                              command=lambda k=key: self.sort_by_column(k))
            width = 60
            if key in ("rua", "bairro"):
                width = 150
            elif key == "url":
                width = 220
            elif key in ("preco", "condominio", "iptu"):
                width = 110
            self.tree.column(key, width=width, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self.on_row_double_click)
        self.tree.tag_configure("odd", background="#f7fafc")

    # ---- connection ----------------------------------------------------------
    def initial_connect(self):
        try:
            self.db.connect()
            self.reload_tables()
            self.status_label.config(text="Conectado", foreground="#48bb78")
        except Exception as e:
            # Non-blocking: show status in the sidebar; the user can retry
            # with the "Atualizar" button once MySQL is available.
            self.status_label.config(text="Erro de conexão — clique Atualizar",
                                     foreground="#fc8181")
            self.count_label.config(text=str(e))

    def reload_tables(self):
        if not self.db.is_connected():
            return
        tables = self.db.list_tables()
        self.table_combo["values"] = tables
        if tables:
            self.table_combo.current(0)
            self.on_table_changed()

    def on_table_changed(self):
        table = self.table_combo.get()
        if not table:
            return
        try:
            self.rows = self.db.fetch_all(table)
            self.count_label.config(text=f"{len(self.rows)} registros")
            self.select_category(self.current_category, self.current_category_label())
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler a tabela: {e}")

    def on_refresh(self):
        if not self.db.is_connected():
            try:
                self.db.connect()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível conectar: {e}")
                return
        self.reload_tables()

    def current_category_label(self):
        for label, key in CATEGORIES.items():
            if key == self.current_category:
                return label
        return "All listings"

    def select_category(self, key, label):
        self.current_category = key
        # visual selection feedback
        for k, btn in self.category_buttons.items():
            btn.state(["!selected"] if k != key else ["selected"])
        self.table_title.config(text=f"Registros — {label}")
        self.current_rows = filter_category(self.rows, key)
        if self.sort_column:
            self.current_rows = sort_rows(self.current_rows, self.sort_column,
                                          self.sort_ascending)
        self.populate_tree(self.current_rows)
        self.populate_metrics(self.current_rows)

    # ---- table population ----------------------------------------------------
    def populate_tree(self, rows):
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(rows):
            values = [str(row.get(key, "") or "") for key, _ in COLUMNS]
            tag = "odd" if idx % 2 else ()
            self.tree.insert("", "end", values=values, tags=tag)

    def populate_metrics(self, rows):
        m = compute_metrics(rows)

        self.metric_values["avg_ppm"].config(text=format_brl(m["avg_ppm"]))
        self.metric_values["avg_price"].config(text=format_brl(m["avg_price"]))
        self.metric_values["avg_area"].config(text=format_num(m["avg_area"]))
        self.metric_values["avg_room"].config(text=format_num(m["avg_room"]))
        self.metric_values["avg_bath"].config(text=format_num(m["avg_bath"]))
        self.metric_values["avg_garage"].config(text=format_num(m["avg_garage"]))

    # ---- interactions ---------------------------------------------------------
    def _update_headings(self):
        """Show a direction arrow on the header used for sorting."""
        for key, head in COLUMNS:
            if key == self.sort_column:
                arrow = " ▲" if self.sort_ascending else " ▼"
                self.tree.heading(key, text=head + arrow)
            else:
                self.tree.heading(key, text=head)

    def sort_by_column(self, column):
        """Sort the visible rows by a column; click again to reverse."""
        if column == self.sort_column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True

        self.current_rows = sort_rows(self.current_rows, column,
                                      self.sort_ascending)
        self._update_headings()
        self.populate_tree(self.current_rows)

    def on_row_double_click(self, _event):
        item = self.tree.selection()
        if not item:
            return
        values = self.tree.item(item[0], "values")
        # Map table display columns back to database keys
        display = dict(zip([k for k, _ in COLUMNS], values))
        url = display.get("url")
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("Sem link", "Este registro não possui URL.")


def main():
    root = tk.Tk()
    ZapGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()