# EV Charging Emission Calculator: Grid Mix to g CO2/km

L&T EduTech EV Mini-Project 5 | Fundamentals of Electric and Hybrid Electric Vehicle Technology | Team 5, SRMU

A desktop app (Python, CustomTkinter, matplotlib) that finds the real CO2 per km of an EV from its charging
electricity mix and compares it with petrol, diesel and hybrid cars.

![App screenshot](docs/screenshot.png)
<!-- Add your screenshot at docs/screenshot.png -->

## What it calculates
- Grid emission factor from the electricity mix (coal, gas, clean) in kg CO2/kWh
- Electricity generated per km after charger and grid losses (Wh/km)
- EV g CO2/km vs petrol g CO2/km, and the percentage difference
- Coal share at which the EV becomes as dirty as petrol (or "never")
- Daily charging energy at the plug (kWh/day)
- Rooftop solar size for zero-emission charging (kWp)
- A final answer sentence, updated live

## Features
- Live updates, no Calculate button
- Three mix sliders that always total 100%
- Tabs for Petrol, Diesel, Pure EV and Hybrid (with fuel type and battery share)
- Comparison chart (g CO2/km), light and dark theme
- Quick start presets, input validation, CSV export
- Editable emission factors and solar yield in Settings

## Formulas
- grid (kg/kWh) = (coal% x 0.95 + gas% x 0.45 + clean% x 0) / 100
- generated Wh/km = battery Wh/km / (charger efficiency x (1 - grid loss))
- EV g/km = generated Wh/km x grid
- Petrol g/km = 2.31 x 1000 / (km per litre)
- plug kWh/day = km x Wh/km / 1000 / charger efficiency
- solar kWp = plug kWh/day / (solar kWh per kWp per day, default 4)
- Break-even coal: gas share fixed, coal replaces clean sources; solve EV g/km = petrol g/km

Defaults: charger 90%, grid loss 18%. Emission factors are approximate operational values.

## Worked example (from the problem statement)
150 Wh/km, petrol 15 km/L, 25 km/day, 40% coal / 10% gas / 50% clean:
EV 86.4 g/km vs petrol 154.0 g/km, break-even 75.0% coal, 4.17 kWh/day, 1.04 kWp solar.

## Run (Python 3.11+)
```
pip install -r requirements.txt
python main.py
```

## Tests
```
python -m unittest -v test_calc
```
21 tests cover the formulas, break-even, solar sizing, edge cases and slider rebalancing.

## Build the Windows .exe
```
python make_icon.py
pyinstaller --noconfirm --onefile --windowed --name CO2Comparator --icon icon.ico --add-data "icon.ico;." --collect-all customtkinter main.py
```
The file is created at `dist/CO2Comparator.exe`.

## Project structure
```
calc.py        pure calculation logic (no UI)
ui.py          CustomTkinter interface
main.py        entry point
test_calc.py   unit tests
make_icon.py   generates icon.ico
```

## Limitations
- Operational emissions only (no manufacturing or lifecycle emissions)
- "Clean" groups hydro, nuclear, solar and wind together at 0 kg CO2/kWh
- Emission factors differ by country and year; cite your source (for example CEA or IPCC)

## License
MIT
