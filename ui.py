"""Desktop UI (CustomTkinter + matplotlib). All maths lives in calc.py."""
import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import calc

rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]

FONT = "Segoe UI"

# (light, dark) colour pairs: CustomTkinter switches them automatically.
BG = ("#F7F8FA", "#111827")
CARD = ("#FFFFFF", "#1F2937")
BORDER = ("#E3E6EB", "#374151")
TEXT = ("#1F2937", "#F3F4F6")
MUTED = ("#6B7280", "#9CA3AF")
ACCENT = ("#0F766E", "#2DD4BF")
ACCENT_HOVER = ("#0B5F58", "#14B8A6")
ACCENT_TINT = ("#CCFBF1", "#134E4A")     # selected tab background (keeps text readable)
ON_ACCENT = ("#FFFFFF", "#111827")
ERROR = ("#DC2626", "#F87171")
COAL, GAS, REN = "#6B7280", "#F59E0B", "#16A34A"
BAR_OTHER = "#94A3B8"

LIMITS = {"distance": (0.1, 2000.0), "mileage": (1.0, 100.0), "wh": (20.0, 2000.0),
          "charger": (50.0, 100.0), "gridloss": (0.0, 50.0)}
TAB_TITLES = {"Petrol": "Petrol car", "Diesel": "Diesel car", "Pure EV": "Pure electric car"}


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def card(parent):
    return ctk.CTkFrame(parent, fg_color=CARD, border_color=BORDER,
                        border_width=1, corner_radius=12)


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("system")      # follow the OS theme on first launch
        super().__init__()
        self.title("Vehicle CO2 Emission Comparator")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=BG)
        self.after(250, self._set_icon)

        self.settings = dict(calc.DEFAULT_SETTINGS)
        self.mix = dict(calc.DEFAULT_MIX)
        self.vals = dict(calc.DEFAULT_INPUTS)        # last valid values
        self.fields = {}
        self.sliders = {}
        self.pct_labels = {}
        self.tab_var = ctk.StringVar(value="Petrol")
        self.hy_fuel = ctk.StringVar(value="Petrol")
        self.hy_share = ctk.DoubleVar(value=50.0)

        self.f_body = ctk.CTkFont(family=FONT, size=14)
        self.f_bold = ctk.CTkFont(family=FONT, size=14, weight="bold")
        self.f_small = ctk.CTkFont(family=FONT, size=12)
        self.f_head = ctk.CTkFont(family=FONT, size=20, weight="bold")
        self.f_big = ctk.CTkFont(family=FONT, size=36, weight="bold")
        self.menu_style = dict(font=self.f_body, dropdown_font=self.f_body, fg_color=BG,
                               button_color=BORDER, button_hover_color=MUTED,
                               text_color=TEXT, dropdown_fg_color=CARD,
                               dropdown_text_color=TEXT, dropdown_hover_color=BORDER)

        self.columnconfigure(0, weight=35, uniform="cols")
        self.columnconfigure(1, weight=65, uniform="cols")
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_left()
        self._build_right()

        for f in self.fields.values():           # live updates, no Calculate button
            f["var"].trace_add("write", lambda *_: self.refresh())
        self.refresh()

    # ------------------------------------------------------------------ build
    def _set_icon(self):
        path = resource_path("icon.ico")
        if os.path.exists(path):
            try:
                self.iconbitmap(path)
            except tk.TclError:
                pass

    def _heading(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=self.f_head, text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 6))

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 8))
        bar.columnconfigure(0, weight=1)
        ctk.CTkLabel(bar, text="Vehicle CO2 Emission Comparator", font=self.f_head,
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        self.theme_switch = ctk.CTkSwitch(bar, text="Dark mode", font=self.f_body,
                                          text_color=TEXT, progress_color=ACCENT,
                                          command=self.toggle_theme)
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        self.theme_switch.grid(row=0, column=1, sticky="e")

    def _field(self, parent, key, label, helper):
        ctk.CTkLabel(parent, text=label, font=self.f_body, text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        var = ctk.StringVar(value=f"{self.vals[key]:g}")
        entry = ctk.CTkEntry(parent, textvariable=var, font=self.f_body, height=32,
                             fg_color=BG, border_color=BORDER, text_color=TEXT)
        entry.pack(fill="x", padx=16, pady=(2, 0))
        msg = ctk.CTkLabel(parent, text=helper, font=self.f_small, text_color=MUTED,
                           anchor="w", justify="left", wraplength=300)
        msg.pack(fill="x", padx=16, pady=(2, 0))
        self.fields[key] = {"var": var, "entry": entry, "msg": msg, "helper": helper}

    def _build_left(self):
        left = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        # Card 1: driving
        c1 = card(left)
        c1.pack(fill="x", pady=(0, 12))
        self._heading(c1, "1. Your driving")
        self.preset_menu = ctk.CTkOptionMenu(c1, values=list(calc.PRESETS),
                                             command=self.apply_preset, **self.menu_style)
        self.preset_menu.set("Quick start: pick an example car")
        self.preset_menu.pack(fill="x", padx=16, pady=(0, 4))
        self._field(c1, "distance", "Distance you drive per day (km)",
                    "Typical city commute: 20-50 km")
        self._field(c1, "mileage", "Petrol/Diesel car: km per litre",
                    "Most petrol cars: 12-20 km per litre")
        self._field(c1, "wh", "Electric car: energy used per km (Wh/km)",
                    "Most electric cars: 120-200 Wh per km (measured at the battery)")
        ctk.CTkFrame(c1, height=10, fg_color="transparent").pack()

        # Card 2: electricity
        c2 = card(left)
        c2.pack(fill="x", pady=(0, 12))
        self._heading(c2, "2. Your electricity")
        ctk.CTkLabel(c2, text="How your electricity is made", font=self.f_body,
                     text_color=TEXT, anchor="w").pack(fill="x", padx=16)
        self.grid_menu = ctk.CTkOptionMenu(c2, values=list(calc.GRID_PRESETS),
                                           command=self.apply_grid_preset, **self.menu_style)
        self.grid_menu.set("Quick start: pick a grid")
        self.grid_menu.pack(fill="x", padx=16, pady=(6, 4))
        for key, name, color in (("coal", "Coal", COAL), ("gas", "Gas", GAS),
                                 ("ren", "Renewable", REN)):
            row = ctk.CTkFrame(c2, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            row.columnconfigure(2, weight=1)
            ctk.CTkLabel(row, text="●", text_color=color, font=self.f_body,
                         width=16).grid(row=0, column=0)
            ctk.CTkLabel(row, text=name, font=self.f_body, text_color=TEXT, width=90,
                         anchor="w").grid(row=0, column=1, padx=(4, 0))
            sl = ctk.CTkSlider(row, from_=0, to=100, number_of_steps=100,
                               command=lambda v, k=key: self.on_mix(k, v),
                               progress_color=color, button_color=ACCENT,
                               button_hover_color=ACCENT_HOVER, fg_color=BORDER)
            sl.set(self.mix[key])
            sl.grid(row=0, column=2, sticky="ew", padx=8)
            pct = ctk.CTkLabel(row, text="", font=self.f_body, text_color=TEXT,
                               width=48, anchor="e")
            pct.grid(row=0, column=3)
            self.sliders[key] = sl
            self.pct_labels[key] = pct

        bar = ctk.CTkFrame(c2, height=12, fg_color=BORDER, corner_radius=6)
        bar.pack(fill="x", padx=16, pady=(8, 4))
        bar.pack_propagate(False)
        self.segs = {k: ctk.CTkFrame(bar, fg_color=c, corner_radius=0, height=12)
                     for k, c in (("coal", COAL), ("gas", GAS), ("ren", REN))}
        self.gi_label = ctk.CTkLabel(c2, text="", font=self.f_small, text_color=MUTED,
                                     anchor="w")
        self.gi_label.pack(fill="x", padx=16, pady=(2, 0))
        ctk.CTkLabel(c2, text="The three sliders always add up to 100%.", font=self.f_small,
                     text_color=MUTED, anchor="w").pack(fill="x", padx=16, pady=(0, 4))
        self._field(c2, "charger", "Charger efficiency (%)",
                    "Energy lost as heat while charging. Typical: 85-95%")
        self._field(c2, "gridloss", "Grid loss in transmission (%)",
                    "Lost between the power plant and your socket. Default: 18%")
        ctk.CTkFrame(c2, height=10, fg_color="transparent").pack()

        # Buttons
        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.pack(fill="x")
        outline = dict(font=self.f_body, fg_color="transparent", border_width=1,
                       border_color=BORDER, text_color=TEXT, hover_color=BORDER, height=34)
        ctk.CTkButton(btns, text="Reset", width=80, command=self.reset, **outline
                      ).pack(side="left")
        ctk.CTkButton(btns, text="⚙ Settings", width=100, command=self.open_settings,
                      **outline).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Export CSV", font=self.f_body, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                      command=self.export_csv).pack(side="right")

    def _build_right(self):
        right = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        right.columnconfigure(0, weight=1)

        # Banner
        self.banner = card(right)
        self.banner.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(self.banner, text="Change any value on the left and watch the "
                     "results update instantly.", font=self.f_body, text_color=TEXT
                     ).pack(side="left", padx=16, pady=8)
        ctk.CTkButton(self.banner, text="✕", width=28, height=28, fg_color="transparent",
                      hover_color=BORDER, text_color=MUTED, font=self.f_body,
                      command=self.banner.grid_remove).pack(side="right", padx=8)

        # Result card
        rc = card(right)
        rc.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._heading(rc, "3. See the result")
        ctk.CTkSegmentedButton(rc, values=list(calc.OPTIONS), variable=self.tab_var,
                               command=lambda _v: self.refresh(), font=self.f_body,
                               fg_color=BG, selected_color=ACCENT_TINT,
                               selected_hover_color=ACCENT_TINT, unselected_color=BG,
                               unselected_hover_color=BORDER, text_color=TEXT
                               ).pack(anchor="w", padx=16, pady=(0, 8))
        body = ctk.CTkFrame(rc, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(0, 14))
        body.columnconfigure(0, weight=1, uniform="r")
        body.columnconfigure(1, weight=1, uniform="r")

        num = ctk.CTkFrame(body, fg_color="transparent")
        num.grid(row=0, column=0, sticky="nw")
        self.title_lbl = ctk.CTkLabel(num, text="", font=self.f_bold, text_color=MUTED,
                                      anchor="w")
        self.title_lbl.pack(fill="x")
        self.big_lbl = ctk.CTkLabel(num, text="", font=self.f_big, text_color=ACCENT,
                                    anchor="w")
        self.big_lbl.pack(fill="x")
        self.period_lbl = ctk.CTkLabel(num, text="", font=self.f_body, text_color=TEXT,
                                       anchor="w", justify="left")
        self.period_lbl.pack(fill="x")
        self.tree_lbl = ctk.CTkLabel(num, text="", font=self.f_small, text_color=MUTED,
                                     anchor="w", justify="left", wraplength=290)
        self.tree_lbl.pack(fill="x", pady=(6, 0))

        self.hy_frame = ctk.CTkFrame(body, fg_color=BG, corner_radius=8)
        self.hy_frame.grid(row=0, column=1, sticky="new", padx=(12, 0))
        ctk.CTkLabel(self.hy_frame, text="Hybrid settings", font=self.f_bold,
                     text_color=TEXT, anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkSegmentedButton(self.hy_frame, values=["Petrol", "Diesel"],
                               variable=self.hy_fuel, command=lambda _v: self.refresh(),
                               font=self.f_body, fg_color=CARD, selected_color=ACCENT_TINT,
                               selected_hover_color=ACCENT_TINT, unselected_color=CARD,
                               unselected_hover_color=BORDER, text_color=TEXT
                               ).pack(anchor="w", padx=12)
        self.share_lbl = ctk.CTkLabel(self.hy_frame, text="", font=self.f_body,
                                      text_color=TEXT, anchor="w")
        self.share_lbl.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.hy_frame, from_=0, to=100, number_of_steps=100,
                      variable=self.hy_share, command=lambda _v: self.refresh(),
                      progress_color=ACCENT, button_color=ACCENT,
                      button_hover_color=ACCENT_HOVER, fg_color=BORDER
                      ).pack(fill="x", padx=12, pady=(2, 0))
        self.split_lbl = ctk.CTkLabel(self.hy_frame, text="", font=self.f_small,
                                      text_color=MUTED, anchor="w")
        self.split_lbl.pack(fill="x", padx=12, pady=(6, 10))

        # Key numbers (units section)
        kc = card(right)
        kc.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(kc, text="Key numbers", font=self.f_head, text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 6))
        tg = ctk.CTkFrame(kc, fg_color="transparent")
        tg.pack(fill="x", padx=12, pady=(0, 12))
        for c in range(3):
            tg.columnconfigure(c, weight=1, uniform="k")
        self.tiles = {}
        tile_defs = [("gef", "Grid emission factor (feeds Project 2)"),
                     ("gen", "Electricity generated per km (after losses)"),
                     ("ev", "EV CO\u2082 per km"),
                     ("pet", "Petrol CO\u2082 per km"),
                     ("be", "Break-even coal share"),
                     ("plug", "Daily charging energy at the plug"),
                     ("solar", "Rooftop solar for zero-emission charging")]
        for i, (key, name) in enumerate(tile_defs):
            tile = ctk.CTkFrame(tg, fg_color=BG, corner_radius=8)
            tile.grid(row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4)
            ctk.CTkLabel(tile, text=name, font=self.f_small, text_color=MUTED, anchor="w",
                         justify="left", wraplength=170).pack(fill="x", padx=10, pady=(8, 0))
            val = ctk.CTkLabel(tile, text="", font=self.f_bold, text_color=TEXT, anchor="w",
                               justify="left", wraplength=170)
            val.pack(fill="x", padx=10, pady=(0, 8))
            self.tiles[key] = val

        # Final answer
        fc = card(right)
        fc.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(fc, text="Final answer", font=self.f_head, text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 6))
        self.final_lbl = ctk.CTkLabel(fc, text="", font=self.f_body, text_color=TEXT,
                                      anchor="w", justify="left", wraplength=600)
        self.final_lbl.pack(fill="x", padx=16, pady=(0, 14))
        self._wrap = 600

        def fit_final(event):
            width = max(event.width - 40, 200)
            if width != self._wrap:
                self._wrap = width
                self.final_lbl.configure(wraplength=width)
        fc.bind("<Configure>", fit_final)

        # Highlight
        hc = card(right)
        hc.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        self.highlight_lbl = ctk.CTkLabel(hc, text="", font=self.f_bold, text_color=TEXT,
                                          anchor="w")
        self.highlight_lbl.pack(fill="x", padx=16, pady=10)

        # Chart
        cc = card(right)
        cc.grid(row=5, column=0, sticky="ew")
        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=cc)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(8, 0))
        ctk.CTkLabel(cc, text="Lower is better. Green bar = cleanest option.",
                     font=self.f_small, text_color=MUTED).pack(pady=(0, 8))

    # ---------------------------------------------------------------- actions
    def toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")
        self.after(50, self.draw_chart)

    def apply_preset(self, name):
        p = calc.PRESETS[name]
        self.fields["distance"]["var"].set(f"{p['distance']:g}")
        self.fields["mileage"]["var"].set(f"{p['mileage']:g}")
        self.fields["wh"]["var"].set(f"{p['wh']:g}")
        self.tab_var.set(p["tab"])
        if "battery_share" in p:
            self.hy_share.set(p["battery_share"])
        self.refresh()

    def apply_grid_preset(self, name):
        self.mix = dict(calc.GRID_PRESETS[name])
        self._sync_sliders()
        self.refresh()

    def on_mix(self, key, value):
        self.mix = calc.rebalance(self.mix, key, value)
        self._sync_sliders()
        self.refresh()

    def _sync_sliders(self):
        for k, sl in self.sliders.items():
            sl.set(self.mix[k])

    def reset(self):
        for k, v in calc.DEFAULT_INPUTS.items():
            self.fields[k]["var"].set(f"{v:g}")
        self.mix = dict(calc.DEFAULT_MIX)
        self._sync_sliders()
        self.hy_share.set(50.0)
        self.hy_fuel.set("Petrol")
        self.tab_var.set("Petrol")
        self.preset_menu.set("Quick start: pick an example car")
        self.grid_menu.set("Quick start: pick a grid")
        self.refresh()

    # ------------------------------------------------------------ validation
    def _check_fields(self):
        for key, f in self.fields.items():
            lo, hi = LIMITS[key]
            try:
                v = float(f["var"].get().strip().replace(",", "."))
                if not lo <= v <= hi:
                    raise ValueError
            except ValueError:
                f["entry"].configure(border_color=ERROR)
                f["msg"].configure(text=f"Please enter a number between {lo:g} and {hi:g}",
                                   text_color=ERROR)
            else:
                self.vals[key] = v
                f["entry"].configure(border_color=BORDER)
                f["msg"].configure(text=f["helper"], text_color=MUTED)

    # --------------------------------------------------------------- refresh
    def refresh(self):
        self._check_fields()
        v = self.vals
        s = dict(self.settings, charging_efficiency=v["charger"] / 100.0,
                 grid_loss=v["gridloss"] / 100.0)
        res = calc.compare(v["distance"], v["mileage"], v["wh"] / 1000.0, self.mix,
                           self.hy_share.get() / 100.0, self.hy_fuel.get(), s)
        self.res = res
        totals = res["totals"]
        sm = calc.summary(v["distance"], v["mileage"], v["wh"], self.mix, s)
        self.sm = sm

        pcts = calc.display_percents(self.mix)
        for k, lbl in self.pct_labels.items():
            lbl.configure(text=f"{pcts[k]}%")
        x = 0.0
        for k in ("coal", "gas", "ren"):
            w = max(self.mix[k] / 100.0, 0.0001)
            self.segs[k].place(relx=x, rely=0, relwidth=w, relheight=1)
            x += self.mix[k] / 100.0
        self.gi_label.configure(text=f"Grid intensity: {res['intensity']:.2f} kg CO2 per kWh")

        tab = self.tab_var.get()
        day, month, year = calc.per_period(totals[tab])
        title = (f"Hybrid car ({self.hy_fuel.get()} + battery)" if tab == "Hybrid"
                 else TAB_TITLES[tab])
        self.title_lbl.configure(text=title)
        self.big_lbl.configure(text=f"{day:.2f} kg CO2 / day")
        gkm = day * 1000.0 / v["distance"]
        self.period_lbl.configure(text=f"{gkm:.1f} g per km\n"
                                       f"{month:,.2f} kg per month   |   {year:,.2f} kg per year")
        self.tree_lbl.configure(text=calc.tree_sentence(day, self.settings))

        if tab == "Hybrid":
            self.hy_frame.grid()
        else:
            self.hy_frame.grid_remove()
        share = self.hy_share.get()
        self.share_lbl.configure(text=f"Share of trip on battery: {share:.0f}%")
        h = res["hybrid"]
        self.split_lbl.configure(text=f"Fuel: {h['fuel']:.2f} kg  |  Battery: {h['battery']:.2f} kg")

        best, pct = calc.lowest(totals)
        label = {"Pure EV": "Pure EV"}.get(best, best)
        text = f"Lowest emission: {label}, {totals[best] * 1000.0 / v['distance']:.1f} g CO2 / km"
        if pct is not None:
            text += f" ({pct:.0f}% less than Petrol)"
        self.highlight_lbl.configure(text=text)

        if sm["be_status"] == "value":
            be_text = f"{sm['be']:.1f}% coal"
        elif sm["be_status"] == "never":
            be_text = "Never (EV stays cleaner)"
        else:
            be_text = "Already dirtier at 0% coal"
        cmp_word = "lower" if sm["pct"] <= 0 else "higher"
        self.tiles["gef"].configure(text=f"{sm['gi']:.3f} kg CO\u2082/kWh")
        self.tiles["gen"].configure(text=f"{sm['gen_wh']:.1f} Wh/km")
        self.tiles["ev"].configure(
            text=f"{sm['ev_g']:.1f} g CO\u2082/km\n({abs(sm['pct']):.0f}% {cmp_word} than petrol)")
        self.tiles["pet"].configure(text=f"{sm['petrol_g']:.1f} g CO\u2082/km")
        self.tiles["be"].configure(text=be_text)
        self.tiles["plug"].configure(text=f"{sm['plug_kwh']:.2f} kWh/day")
        self.tiles["solar"].configure(text=f"{sm['kwp']:.2f} kWp")
        self.final_lbl.configure(text=calc.final_answer(sm))
        self.draw_chart()

    def draw_chart(self):
        if not hasattr(self, "res"):
            return
        dark = ctk.get_appearance_mode() == "Dark"
        bg, fg = ("#1F2937", "#F3F4F6") if dark else ("#FFFFFF", "#1F2937")
        muted, edge = ("#9CA3AF", "#374151") if dark else ("#6B7280", "#E3E6EB")
        totals = self.res["totals"]
        names = list(totals)
        vals = [totals[n] * 1000.0 / self.vals["distance"] for n in names]
        best = min(totals, key=totals.get)

        self.fig.set_facecolor(bg)
        self.canvas.get_tk_widget().configure(bg=bg)
        ax = self.ax
        ax.clear()
        ax.set_facecolor(bg)
        bars = ax.bar(names, vals, width=0.55,
                      color=[REN if n == best else BAR_OTHER for n in names])
        top = max(vals) if max(vals) > 0 else 1.0
        for b, val in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, val + top * 0.02, f"{val:.1f}",
                    ha="center", va="bottom", color=fg, fontsize=10, fontweight="bold")
        ax.set_ylim(0, top * 1.2)
        ax.set_yticks([])
        ax.set_ylabel("g CO2 per km", color=muted, fontsize=10)
        ax.tick_params(axis="x", colors=fg, length=0, labelsize=10)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(edge)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ---------------------------------------------------------------- export
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV file", "*.csv")],
                                            initialfile="co2_results.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["Option", "kg CO2 per day", "kg CO2 per month (x30)",
                            "kg CO2 per year (x365)"])
                for name, val in self.res["totals"].items():
                    d, m, y = calc.per_period(val)
                    w.writerow([name, f"{d:.3f}", f"{m:.2f}", f"{y:.2f}"])
                w.writerow([])
                w.writerow(["Input", "Value"])
                w.writerow(["Distance per day (km)", self.vals["distance"]])
                w.writerow(["Mileage (km/l)", self.vals["mileage"]])
                w.writerow(["EV consumption at battery (Wh/km)", self.vals["wh"]])
                w.writerow(["Charger efficiency (%)", self.vals["charger"]])
                w.writerow(["Grid loss (%)", self.vals["gridloss"]])
                for k, label in (("coal", "Coal %"), ("gas", "Gas %"), ("ren", "Renewable %")):
                    w.writerow([label, f"{self.mix[k]:.1f}"])
                w.writerow(["Grid intensity (kg CO2/kWh)", f"{self.res['intensity']:.3f}"])
                w.writerow(["Electricity generated per km (Wh/km)", f"{self.sm['gen_wh']:.1f}"])
                w.writerow(["EV CO2 (g/km)", f"{self.sm['ev_g']:.2f}"])
                w.writerow(["Petrol CO2 (g/km)", f"{self.sm['petrol_g']:.2f}"])
                w.writerow(["Daily charging energy at plug (kWh/day)", f"{self.sm['plug_kwh']:.2f}"])
                w.writerow(["Rooftop solar for zero emission (kWp)", f"{self.sm['kwp']:.2f}"])
                w.writerow(["Final answer", calc.final_answer(self.sm)])
                w.writerow(["Hybrid fuel", self.hy_fuel.get()])
                w.writerow(["Hybrid battery share %", f"{self.hy_share.get():.0f}"])
                w.writerow([])
                w.writerow(["Emission factor", "Value"])
                for k, val in self.settings.items():
                    w.writerow([k, val])
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))

    # -------------------------------------------------------------- settings
    def open_settings(self):
        if getattr(self, "_dlg", None) is not None and self._dlg.winfo_exists():
            self._dlg.focus()
            return
        dlg = ctk.CTkToplevel(self)
        self._dlg = dlg
        dlg.title("Settings")
        dlg.geometry("420x520")
        dlg.configure(fg_color=BG)
        dlg.transient(self)
        ctk.CTkLabel(dlg, text="Advanced settings", font=self.f_head, text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(dlg, text="Emission factors are approximate and differ by country.",
                     font=self.f_small, text_color=MUTED).pack(anchor="w", padx=20)

        rows = [("ef_petrol", "Petrol (kg CO2 per litre)"),
                ("ef_diesel", "Diesel (kg CO2 per litre)"),
                ("ef_coal", "Coal electricity (kg CO2 per kWh)"),
                ("ef_gas", "Gas electricity (kg CO2 per kWh)"),
                ("ef_ren", "Renewable electricity (kg CO2 per kWh)"),
                ("solar_kwh_per_kwp_day", "Solar generation per kWp per day (kWh)"),
                ("tree_kg_per_year", "CO2 absorbed by 1 tree per year (kg)")]
        entries = {}
        for key, label in rows:
            ctk.CTkLabel(dlg, text=label, font=self.f_body, text_color=TEXT, anchor="w"
                         ).pack(fill="x", padx=20, pady=(8, 0))
            e = ctk.CTkEntry(dlg, font=self.f_body, height=30, fg_color=CARD,
                             border_color=BORDER, text_color=TEXT)
            e.insert(0, f"{self.settings[key]:g}")
            e.pack(fill="x", padx=20)
            entries[key] = e
        err = ctk.CTkLabel(dlg, text="", font=self.f_small, text_color=ERROR, anchor="w")
        err.pack(fill="x", padx=20, pady=(6, 0))

        def save():
            new = {}
            for key, e in entries.items():
                try:
                    val = float(e.get().strip().replace(",", "."))
                except ValueError:
                    err.configure(text="All fields must be numbers.")
                    return
                if val < 0 or (key == "solar_kwh_per_kwp_day" and val <= 0):
                    err.configure(text="Please check the values (no negatives; "
                                       "solar yield must be above 0).")
                    return
                new[key] = val
            self.settings.update(new)
            dlg.destroy()
            self.refresh()

        def defaults():
            for key, e in entries.items():
                e.delete(0, "end")
                e.insert(0, f"{calc.DEFAULT_SETTINGS[key]:g}")
            err.configure(text="")

        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(row, text="Reset to defaults", font=self.f_body, fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=TEXT,
                      hover_color=BORDER, command=defaults).pack(side="left")
        ctk.CTkButton(row, text="Save", font=self.f_body, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, text_color=ON_ACCENT, command=save
                      ).pack(side="right")
