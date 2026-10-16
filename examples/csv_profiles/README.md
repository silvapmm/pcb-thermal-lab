# Example: power profiles from CSV files

A small, fully documented example of how to describe the power of each component over time with **CSV files**.
The board is the 100 x 80 mm, 4-layer board used by the tests: two heaters (U1 and U2), a 3 x 3 via array under U1, partial top copper and a sink on the bottom.

```
examples/csv_profiles/
  board.pcbt.json                      the board (made by make_board.py)
  profiles/u1_motor_driver_cycle.csv   U1: repeating 30 s work cycle (a table that repeats)
  profiles/u2_regulator_startup.csv    U2: start-up after switch-on (a one-shot table)
  profiles/u2_pwm_1khz.csv             U2, alternative: 1 kHz switching load (the program averages it)
  make_board.py                        writes board.pcbt.json
  run_example.py                       runs the example with the Python API
```

## The CSV format

```
# free comment lines start with #
# repeat: yes                  <- yes: the table repeats; no: it runs once and the last power is held
time_s,power_w
0,12.0
2,5.0
10,0.5
30,0.5                         <- the last row is the END of the profile; its power is ignored
```

* Row *i* gives the power **from its time until the next row** (the power is constant in between, a step, not a ramp).
* The first time must be **0** and the times must increase. Powers cannot be negative.
* Optional units in the header: `time_s`, `time_ms`, `time_us`, `time_min`, `time_h` and `power_w`, `power_mw`, `power_kw`. Separators: comma, semicolon or tab; the decimal separator is a point.
* `repeat: yes` is a **periodic load**: its average power is used by the steady-state models, and the program decides whether the board sees only the average or the oscillation (see below).
  `repeat: no` is a **one-shot profile** (start-up, mission): it is always simulated in time, from its start state; after the end the last power is held.

## Scenario 1: motor driver cycle (U1) and regulator start-up (U2)

U1 draws 12 W for 2 s, then 5 W for 8 s, then 0.5 W for 20 s, and repeats every 30 s (average 2.47 W).
U2 is off for 10 s, has a 3 W inrush for 10 s and then runs at 1.5 W; it is a one-shot profile of 300 s.

Run it with the command line:

```sh
.venv/bin/python -m pcbthermal run examples/csv_profiles/board.pcbt.json \
    --profile U1=examples/csv_profiles/profiles/u1_motor_driver_cycle.csv \
    --profile U2=examples/csv_profiles/profiles/u2_regulator_startup.csv --out output
```

or with Python (`.venv/bin/python examples/csv_profiles/run_example.py`), or in the application:

1. open `board.pcbt.json` (File > Open);
2. tab **Power profile**, select U1, press **Import CSV…** and choose the first file; repeat for U2;
3. press **Analyze regimes** to see the decision, then **Run simulation** (F5); the **Results > Power profile** tab shows temperature versus time, the peak map and the last window frame by frame.

What to expect (FVM, 1 mm cells; the three models agree within 4 %):

| Quantity | Value |
| :-- | --: |
| Steady temperature with the average powers | 66.5 °C |
| Peak during the run (U1 at the end of its 12 W stretch) | 119.5 °C (Lumped 116.1, Analytic 115.1) |
| Lowest hottest-point temperature | 61.1 °C |
| Steady temperature if the peak powers were applied constantly (the bound) | 201.6 °C |

The decision table says both heaters are **resolved** (their oscillation, 72.8 °C and 45.9 °C, is far above the 1 °C threshold), so nothing is replaced by an average.
U2 starts at the steady state of its *first* power (0 W), i.e. only warmed by U1, and the plot shows the inrush and the settling.

## Scenario 2: a fast switching load (average is enough)

Replace the U2 file by `u2_pwm_1khz.csv` (1 kHz, 30 % duty, 5 W while on): `python examples/csv_profiles/run_example.py pwm`.
The oscillation caused at the hottest point of U2 is about 0.04 °C, below the threshold, so the program **averages it to 1.5 W** and simulates only U1 in time.
Try changing the threshold (Power profile tab, "Ignore oscillations below", or `--threshold-c 0`) to force the full-resolution run and compare the results and the computing time (the 1 kHz wave then needs thousands of steps per cycle).

## Exporting

In the application, **Export CSV…** writes the profile of the selected heater (a square wave is written as a table), so a profile can be edited in a spreadsheet and imported again.
A table is edited in its CSV file; the application shows its summary (stretches, length, average, peak, energy).

## Notes

* Generated results (`output_*` folders) are not kept in the repository.
* The three files are valid examples for the tests (`tests/test_profiles.py`).
