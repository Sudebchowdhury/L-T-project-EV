import unittest
import calc

S = calc.DEFAULT_SETTINGS
EFF = S["charging_efficiency"] * (1 - S["grid_loss"])      # 0.9 x 0.82
PDF_MIX = {"coal": 40.0, "gas": 10.0, "ren": 50.0}          # example from the problem statement


class CalcTests(unittest.TestCase):
    def test_petrol_diesel(self):
        self.assertAlmostEqual(calc.fuel_co2(25, 15, "Petrol", S), 25 / 15 * 2.31)
        self.assertAlmostEqual(calc.fuel_co2(25, 15, "Diesel", S), 25 / 15 * 2.68)

    def test_grid_intensity(self):
        self.assertAlmostEqual(calc.grid_intensity({"coal": 100, "gas": 0, "ren": 0}, S), 0.95)
        self.assertAlmostEqual(calc.grid_intensity({"coal": 0, "gas": 0, "ren": 100}, S), 0.0)
        self.assertAlmostEqual(calc.grid_intensity({"coal": 50, "gas": 50, "ren": 0}, S), 0.70)

    def test_ev_includes_losses(self):
        self.assertAlmostEqual(calc.electric_co2(25, 0.15, 0.7, S), 25 * 0.15 / EFF * 0.7)

    def test_hybrid_extremes(self):
        gi = 0.6
        h0 = calc.hybrid_co2(30, 20, 0.14, 0.0, "Petrol", gi, S)
        h1 = calc.hybrid_co2(30, 20, 0.14, 1.0, "Petrol", gi, S)
        self.assertAlmostEqual(h0["total"], calc.fuel_co2(30, 20, "Petrol", S))
        self.assertAlmostEqual(h1["total"], calc.electric_co2(30, 0.14, gi, S))

    def test_hybrid_split(self):
        h = calc.hybrid_co2(40, 20, 0.15, 0.5, "Diesel", 0.5, S)
        self.assertAlmostEqual(h["fuel"], 20 / 20 * 2.68)
        self.assertAlmostEqual(h["battery"], 20 * 0.15 / EFF * 0.5)
        self.assertAlmostEqual(h["total"], h["fuel"] + h["battery"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            calc.fuel_co2(10, 0, "Petrol", S)
        with self.assertRaises(ValueError):
            calc.hybrid_co2(10, 15, 0.15, 1.5, "Petrol", 0.5, S)

    def test_rebalance_sums_to_100(self):
        mix = {"coal": 55.0, "gas": 20.0, "ren": 25.0}
        out = calc.rebalance(mix, "coal", 80)
        self.assertAlmostEqual(sum(out.values()), 100.0)
        self.assertEqual(out["coal"], 80)
        self.assertAlmostEqual(out["gas"] / out["ren"], 20 / 25)

    def test_rebalance_others_zero(self):
        out = calc.rebalance({"coal": 100.0, "gas": 0.0, "ren": 0.0}, "coal", 60)
        self.assertAlmostEqual(out["gas"], 20.0)
        self.assertAlmostEqual(out["ren"], 20.0)

    def test_display_percents(self):
        p = calc.display_percents({"coal": 33.4, "gas": 33.3, "ren": 33.3})
        self.assertEqual(sum(p.values()), 100)

    def test_lowest(self):
        best, pct = calc.lowest({"Petrol": 4.0, "Diesel": 4.5, "Pure EV": 1.0, "Hybrid": 2.0})
        self.assertEqual(best, "Pure EV")
        self.assertAlmostEqual(pct, 75.0)

    def test_compare_keys(self):
        r = calc.compare(25, 15, 0.15, calc.DEFAULT_MIX, 0.5, "Petrol", S)
        self.assertEqual(set(r["totals"]), set(calc.OPTIONS))

    # ---- assignment checks (Project 5) ----
    def test_pdf_example_numbers(self):
        sm = calc.summary(25, 15, 150, PDF_MIX, S)
        self.assertAlmostEqual(sm["gi"], 0.425)
        self.assertAlmostEqual(sm["gen_wh"], 150 / 0.738)
        self.assertAlmostEqual(sm["ev_g"], 86.38, places=2)       # about 87 on the PDF graph
        self.assertAlmostEqual(sm["petrol_g"], 154.0)

    def test_break_even_is_75_percent(self):
        sm = calc.summary(25, 15, 150, PDF_MIX, S)
        self.assertEqual(sm["be_status"], "value")
        self.assertAlmostEqual(sm["be"], 75.0, places=1)           # matches the PDF graph

    def test_break_even_really_equals_petrol(self):
        sm = calc.summary(25, 15, 150, PDF_MIX, S)
        mix = {"coal": sm["be"], "gas": 10.0, "ren": 90.0 - sm["be"]}
        again = calc.summary(25, 15, 150, mix, S)
        self.assertAlmostEqual(again["ev_g"], again["petrol_g"], places=6)

    def test_break_even_never(self):
        sm = calc.summary(25, 5, 150, PDF_MIX, S)                  # thirsty petrol car
        self.assertEqual(sm["be_status"], "never")

    def test_break_even_already_dirtier(self):
        sm = calc.summary(25, 40, 150, {"coal": 0.0, "gas": 90.0, "ren": 10.0}, S)
        self.assertEqual(sm["be_status"], "already")

    def test_plug_energy_and_solar(self):
        sm = calc.summary(25, 15, 150, PDF_MIX, S)
        self.assertAlmostEqual(sm["plug_kwh"], 25 * 0.150 / 0.90)  # 4.1667 kWh/day
        self.assertAlmostEqual(sm["kwp"], sm["plug_kwh"] / 4.0)

    def test_full_renewable_is_zero(self):
        sm = calc.summary(25, 15, 150, {"coal": 0.0, "gas": 0.0, "ren": 100.0}, S)
        self.assertAlmostEqual(sm["ev_g"], 0.0)

    def test_losses_and_consumption_raise_emissions(self):
        base = calc.summary(25, 15, 150, PDF_MIX, S)["ev_g"]
        lossy = calc.summary(25, 15, 150, PDF_MIX, dict(S, grid_loss=0.30))["ev_g"]
        hungry = calc.summary(25, 15, 200, PDF_MIX, S)["ev_g"]
        self.assertGreater(lossy, base)
        self.assertGreater(hungry, base)

    def test_g_per_km_matches_daily_kg(self):
        sm = calc.summary(25, 15, 150, PDF_MIX, S)
        kg_day = calc.electric_co2(25, 0.150, sm["gi"], S)
        self.assertAlmostEqual(kg_day * 1000 / 25, sm["ev_g"])

    def test_final_answer_text(self):
        txt = calc.final_answer(calc.summary(25, 15, 150, PDF_MIX, S))
        self.assertIn("86.4 g", txt)
        self.assertIn("154.0 g/km", txt)
        self.assertIn("Above 75.0% coal", txt)
        self.assertIn("1.04 kWp", txt)


if __name__ == "__main__":
    unittest.main()
