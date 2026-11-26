"""Pure calculation logic for the CO2 comparator. No UI code in this file."""

DEFAULT_SETTINGS = {
    "ef_petrol": 2.31,            # kg CO2 per litre of petrol
    "ef_diesel": 2.68,            # kg CO2 per litre of diesel
    "ef_coal": 0.95,              # kg CO2 per kWh (coal electricity)
    "ef_gas": 0.45,               # kg CO2 per kWh (gas electricity)
    "ef_ren": 0.0,                # kg CO2 per kWh (renewable; lifecycle ~0.03)
    "charging_efficiency": 0.90,  # charger efficiency (fraction)
    "grid_loss": 0.18,            # transmission and distribution loss (fraction)
    "solar_kwh_per_kwp_day": 4.0, # rooftop solar yield, kWh per kWp per day
    "tree_kg_per_year": 21.0,     # approximate CO2 absorbed by one tree per year
}

DEFAULT_MIX = {"coal": 55.0, "gas": 20.0, "ren": 25.0}
DEFAULT_INPUTS = {"distance": 25.0, "mileage": 15.0, "wh": 150.0,
                  "charger": 90.0, "gridloss": 18.0}
OPTIONS = ("Petrol", "Diesel", "Pure EV", "Hybrid")
DAYS_PER_MONTH = 30
DAYS_PER_YEAR = 365

PRESETS = {
    "Small petrol car":     {"distance": 25, "mileage": 18, "wh": 150, "tab": "Petrol"},
    "Family SUV (diesel)":  {"distance": 40, "mileage": 12, "wh": 220, "tab": "Diesel"},
    "Small electric car":   {"distance": 25, "mileage": 15, "wh": 130, "tab": "Pure EV"},
    "Electric SUV":         {"distance": 40, "mileage": 15, "wh": 200, "tab": "Pure EV"},
    "Hybrid sedan":         {"distance": 30, "mileage": 20, "wh": 140, "tab": "Hybrid",
                             "battery_share": 40},
}

# Approximate shares, editable by the user with the sliders.
GRID_PRESETS = {
    "India grid (approx.)":    {"coal": 72.0, "gas": 3.0, "ren": 25.0},
    "Mostly renewable grid":   {"coal": 10.0, "gas": 15.0, "ren": 75.0},
    "Balanced default":        dict(DEFAULT_MIX),
}


def grid_intensity(mix, s):
    """kg CO2 per kWh of the electricity mix (mix values are percentages)."""
    total = mix["coal"] + mix["gas"] + mix["ren"]
    if total <= 0:
        return 0.0
    return (mix["coal"] * s["ef_coal"] + mix["gas"] * s["ef_gas"]
            + mix["ren"] * s["ef_ren"]) / total


def fuel_co2(distance, mileage_kmpl, fuel, s):
    """kg CO2 for a petrol/diesel car driving `distance` km."""
    if mileage_kmpl <= 0:
        raise ValueError("mileage must be greater than zero")
    if distance < 0:
        raise ValueError("distance cannot be negative")
    ef = s["ef_petrol"] if fuel == "Petrol" else s["ef_diesel"]
    return distance / mileage_kmpl * ef


def electric_co2(distance, kwh_per_km, intensity, s):
    """kg CO2 for an electric drive of `distance` km."""
    if distance < 0 or kwh_per_km < 0:
        raise ValueError("values cannot be negative")
    eff = s["charging_efficiency"] * (1 - s["grid_loss"])
    if eff <= 0:
        raise ValueError("losses must leave some usable energy")
    kwh_generated = distance * kwh_per_km / eff   # at the power station
    return kwh_generated * intensity


def hybrid_co2(distance, mileage_kmpl, kwh_per_km, battery_share, fuel, intensity, s):
    """battery_share is a fraction 0..1. Returns fuel, battery and total kg CO2."""
    if not 0 <= battery_share <= 1:
        raise ValueError("battery_share must be between 0 and 1")
    f = fuel_co2(distance * (1 - battery_share), mileage_kmpl, fuel, s)
    b = electric_co2(distance * battery_share, kwh_per_km, intensity, s)
    return {"fuel": f, "battery": b, "total": f + b}


def compare(distance, mileage, kwh_per_km, mix, battery_share, hybrid_fuel, s):
    gi = grid_intensity(mix, s)
    hybrid = hybrid_co2(distance, mileage, kwh_per_km, battery_share, hybrid_fuel, gi, s)
    totals = {
        "Petrol": fuel_co2(distance, mileage, "Petrol", s),
        "Diesel": fuel_co2(distance, mileage, "Diesel", s),
        "Pure EV": electric_co2(distance, kwh_per_km, gi, s),
        "Hybrid": hybrid["total"],
    }
    return {"totals": totals, "hybrid": hybrid, "intensity": gi}


def rebalance(mix, changed, new_value):
    """Set mix[changed] to new_value and scale the others so the sum stays 100."""
    new_value = max(0.0, min(100.0, float(new_value)))
    others = [k for k in mix if k != changed]
    remaining = 100.0 - new_value
    old_sum = sum(mix[k] for k in others)
    out = {changed: new_value}
    for k in others:
        out[k] = remaining * mix[k] / old_sum if old_sum > 0 else remaining / len(others)
    return out


def display_percents(mix):
    """Whole-number percentages that always add up to exactly 100."""
    floors = {k: int(v) for k, v in mix.items()}
    rem = 100 - sum(floors.values())
    order = sorted(mix, key=lambda k: mix[k] - floors[k], reverse=True)
    for k in order[:max(rem, 0)]:
        floors[k] += 1
    return floors


def per_period(kg_per_day):
    return kg_per_day, kg_per_day * DAYS_PER_MONTH, kg_per_day * DAYS_PER_YEAR


def lowest(totals):
    """Returns (name_of_lowest, percent_less_than_petrol or None)."""
    best = min(totals, key=totals.get)
    pct = None
    if best != "Petrol" and totals["Petrol"] > 0:
        pct = (totals["Petrol"] - totals[best]) / totals["Petrol"] * 100
    return best, pct


def tree_sentence(kg_per_day, s):
    per_day = s["tree_kg_per_year"] / 365.0
    if per_day <= 0:
        return ""
    days = kg_per_day / per_day
    if days < 60:
        span = f"{days:.0f} days"
    elif days < 730:
        span = f"{days / 30.4:.1f} months"
    else:
        span = f"{days / 365:.1f} years"
    return f"Roughly the CO2 that 1 tree absorbs in {span} (approximate)."


def break_even_coal(petrol_g_km, gen_wh_per_km, gas_pct, s):
    """Coal share (%) where EV g/km equals petrol g/km.

    Gas share is fixed; coal replaces the clean sources.
    Returns (status, value): ("value", pct) | ("never", None) | ("already", None).
    EV g/km = generated Wh/km x grid factor (kg/kWh).
    """
    if gen_wh_per_km <= 0:
        return "never", None
    ef_target = petrol_g_km / gen_wh_per_km
    slope = s["ef_coal"] - s["ef_ren"]
    if slope <= 0:
        return "never", None
    base = gas_pct * s["ef_gas"] + (100.0 - gas_pct) * s["ef_ren"]   # coal = 0%
    coal = (ef_target * 100.0 - base) / slope
    if coal < 0:
        return "already", None
    if coal > 100.0 - gas_pct:
        return "never", None
    return "value", coal


def summary(distance, mileage, wh_per_km, mix, s):
    """Assignment outputs. wh_per_km is the EV consumption at the battery."""
    gi = grid_intensity(mix, s)
    gen_wh = wh_per_km / (s["charging_efficiency"] * (1 - s["grid_loss"]))
    ev_g = gen_wh * gi
    petrol_g = s["ef_petrol"] * 1000.0 / mileage
    plug_kwh = distance * wh_per_km / 1000.0 / s["charging_efficiency"]
    status, be = break_even_coal(petrol_g, gen_wh, mix["gas"], s)
    return {
        "gi": gi, "gen_wh": gen_wh, "ev_g": ev_g, "petrol_g": petrol_g,
        "pct": (ev_g - petrol_g) / petrol_g * 100.0 if petrol_g > 0 else 0.0,
        "plug_kwh": plug_kwh, "kwp": plug_kwh / s["solar_kwh_per_kwp_day"],
        "be_status": status, "be": be,
    }


def final_answer(sm):
    text = (f"On this grid mix the EV emits {sm['ev_g']:.1f} g CO\u2082/km vs. "
            f"{sm['petrol_g']:.1f} g/km for petrol. ")
    if sm["be_status"] == "value":
        text += f"Above {sm['be']:.1f}% coal the EV loses its advantage. "
    elif sm["be_status"] == "never":
        text += "Even with the maximum possible coal share the EV stays cleaner than petrol. "
    else:
        text += "With this gas share the EV is already dirtier than petrol, even with 0% coal. "
    return text + f"A {sm['kwp']:.2f} kWp solar panel makes it zero-emission."
