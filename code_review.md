# Stage 1 Code Review: Original Order Report Program

This review is based on the teacher-provided program as it exists in this repository. The original script is `order_report.py` in the repository root. The input file is `data/orders.csv` (header plus 80 order rows). Generated reports belong in `output/`. The repository also contains a standard Python `.gitignore`. No source-file contents were changed for this review. The original program was run from the repository root so that its real behaviour and generated reports could be recorded.

## Baseline Behaviour

The original program was run from the repository root with:

```text
python order_report.py
```

The environment was Python 3.11.9 with pandas 2.3.3 already installed. No extra packages were needed.

The program completed successfully (exit code 0). The console printed the following Swedish status messages (PowerShell displayed `å` as a replacement character, but the source strings are shown here):

```text
Startar orderrapport
Läste in 80 rader
Sparade overview.csv
Sparade sales_by_category.csv
Sparade sales_by_region.csv
Sparade returns_by_category.csv
Klart
```

The script wrote four CSV reports into `output/`. Those files were inspected but not edited.

### Generated report files

| File | Columns | Data rows | Contents |
| --- | --- | --- | --- |
| `output/overview.csv` | `metric`, `value` | 3 | Whole-dataset totals |
| `output/sales_by_category.csv` | `product_category`, `order_count`, `total_sales`, `returns`, `return_rate` | 4 | Sales and returns by product category, sorted by `total_sales` descending |
| `output/sales_by_region.csv` | `region`, `order_count`, `total_sales`, `returns`, `return_rate` | 5 | Sales and returns by region, sorted by `total_sales` descending |
| `output/returns_by_category.csv` | `product_category`, `order_count`, `returns`, `return_rate` | 4 | Return rates by category, sorted by `return_rate` descending |

### Important baseline values

**Overview**

- `total_sales`: **138036.05**
- `order_count`: **80.0**
- `return_count`: **15.0**

The overview file stores the two counts as floating-point values (`80.0` and `15.0`) because they share a column with the rounded sales total.

**Sales by category**

| product_category | order_count | total_sales | returns | return_rate |
| --- | --- | --- | --- | --- |
| Electronics | 26 | 79589.3 | 7 | 0.269 |
| Sports | 16 | 24416.15 | 2 | 0.125 |
| Home | 17 | 23927.6 | 4 | 0.235 |
| Books | 21 | 10103.0 | 2 | 0.095 |

Category order counts add up to 80. Category returns add up to 15. Category sales add up to 138036.05.

**Sales by region**

| region | order_count | total_sales | returns | return_rate |
| --- | --- | --- | --- | --- |
| South | 24 | 36737.95 | 6 | 0.25 |
| East | 18 | 35585.35 | 3 | 0.167 |
| West | 14 | 32624.8 | 2 | 0.143 |
| North | 23 | 29891.95 | 3 | 0.13 |
| Unknown | 1 | 3196.0 | 1 | 1.0 |

Region order counts add up to 80. Region returns add up to 15. Region sales add up to 138036.05. The `Unknown` row comes from order `O0032`, which has an empty `region` in `data/orders.csv`. The script fills missing regions with `"Unknown"`.

**Returns by category**

| product_category | order_count | returns | return_rate |
| --- | --- | --- | --- |
| Electronics | 26 | 7 | 0.269 |
| Home | 17 | 4 | 0.235 |
| Sports | 16 | 2 | 0.125 |
| Books | 21 | 2 | 0.095 |

These are the same category return figures as `sales_by_category.csv`, re-sorted by return rate instead of sales.

The input file also contains values that the script silently repairs before these totals are produced. Examples include a missing quantity (`O0028`), a missing unit price (`O0062`), a missing discount (`O0013`), the text `unknown` in the discount column (`O0040`), mixed region and category spellings (` north `, `SOUTH`, `electronics `, `HOME`), and mixed return flags (`true`, `false`, `Yes`, `no`, empty). Those repairs are part of the current baseline and must be preserved later unless a later stage is allowed to change meaning.

## Code Review Findings

### 1. One file and one execution block do all of the work

**Observation:** `order_report.py` is a single 221-line script. After two imports and two path constants, almost every step sits inside one top-level `try` block: reading the CSV, checking column names, cleaning fields, calculating line values, building four reports, and writing four files. There are no functions.

**Consequence:** Loading, cleaning, calculation, aggregation, and file output cannot be understood or reused separately. A later change to one report risks breaking another step in the same block. The script also cannot be imported as a library without running the full pipeline.

**Proposal:** Later, split the work into named functions such as load, clean, calculate, summarise, and write. Keep a thin entry point that only connects those steps.

### 2. The script runs immediately when the module is imported

**Observation:** There is no `if __name__ == "__main__":` guard and no `main()` function. Every statement after the constants runs as soon as Python loads the file.

**Consequence:** `import order_report` would reread `data/orders.csv` and overwrite the four report files. That makes interactive exploration, reuse, and later unit tests unsafe.

**Proposal:** Move the pipeline behind a `main()` function and call it only from an `if __name__ == "__main__":` block.

### 3. Input and output paths are hard-coded and depend on the current working directory

**Observation:** The script sets `INPUT_FILE = "data/orders.csv"` and `OUTPUT_FOLDER = "output"`. Both are relative paths. They only work when the process current directory is the repository root.

**Consequence:** Running the same file from another folder, or by double-clicking it, looks for `data/orders.csv` in the wrong place and writes reports to a different `output` folder.

**Proposal:** Later, resolve paths from a configuration object or from the repository root, and allow the input and output locations to be passed in rather than fixed as string literals.

### 4. The script assumes the output folder already exists

**Observation:** Reports are written with `os.path.join(OUTPUT_FOLDER, ...)` and `DataFrame.to_csv(...)`. The script never calls `os.makedirs` or otherwise creates `output`.

**Consequence:** The run succeeded only because `output/` already exists in this repository. In a clean folder the first `to_csv` call would raise `FileNotFoundError`. That error would then be hidden by the broad `except` at the bottom.

**Proposal:** Create the output directory before writing files, or fail with a clear error that names the missing folder.

### 5. Category and region aggregation is copied almost verbatim

**Observation:** The `result1` block groups by `product_category` and calculates `order_count`, `total_sales`, `returns`, and `return_rate`. The `result2` block repeats the same aggregation for `region`. A third block groups by `product_category` again for `returns_by_category.csv`, recalculating `order_count`, `returns`, and `return_rate` without `total_sales`.

**Consequence:** The same rounding, division, and sorting rules exist in three places. A later fix to return-rate rounding or to how orders are counted would have to be repeated by hand. The third report also duplicates information already present in `sales_by_category.csv`.

**Proposal:** Extract one reusable summary function that accepts the grouping column and the requested metrics. Build both category and region reports from that function.

### 6. Operational progress is reported only with `print()`

**Observation:** The script prints Swedish messages such as `"Startar orderrapport"`, `"Läste in"`, `"Sparade overview.csv"`, and `"Klart"`. There is no logging module, no return value, and no structured status object.

**Consequence:** Progress text is mixed with the calculation logic. Callers cannot suppress, redirect, or test these messages easily. The Swedish strings also sit next to English column names and file names, which makes the program’s language inconsistent.

**Proposal:** Keep user messages in one place, or replace them with logging. The processing functions should return data frames rather than printing as they go.

### 7. Exceptions are too broad and the error messages are vague

**Observation:** A missing required column raises a bare `Exception("Fel data")`. The whole pipeline is wrapped in `except Exception as error:`, which only prints `"Något gick fel:"` and the exception object. File errors, pandas errors, and the column check are all treated the same way.

**Consequence:** A missing file, a missing output folder, a bad column, or an unexpected pandas error all look like a single generic failure. The program still exits with code 0 after printing the message, so an automated runner cannot tell that the reports were not written. `"Fel data"` also does not say which columns were missing.

**Proposal:** Catch specific errors, name the missing columns or paths, and re-raise or exit with a non-zero status after logging the problem.

### 8. Invalid and missing values are repaired silently

**Observation:** The cleaning block changes several fields without reporting how many values were replaced:

- empty `region` and `product_category` become `"Unknown"`
- non-numeric `quantity` becomes `1`
- non-numeric `unit_price` becomes the median of the remaining prices
- non-numeric or empty `discount`, including the text `unknown`, becomes `0`
- missing `returned` becomes `"false"`; only `true`, `yes`, `1`, and `ja` count as a return

Those rules were applied to real rows in `data/orders.csv`, including `O0028` (empty quantity), `O0062` (empty unit price), `O0013` (empty discount), `O0040` (`unknown` discount), `O0032` (empty region), and `O0069` (empty returned flag).

**Consequence:** The reports look complete even when source values were invented. A missing quantity of 1 and a median-filled price both change `total_sales`, but nothing in the output says that this happened. Later tests cannot distinguish “clean input” from “input that was repaired”.

**Proposal:** Keep the same repair rules so the current report meanings stay the same, but move them into an explicit cleaning step that records what was changed. Later validation can reject or flag values instead of hiding them.

### 9. Dates and several numeric fields are not really validated

**Observation:** `order_date` is listed in `required`, but it is never parsed with `pd.to_datetime`, checked for missing values, or used in any report. `customer_id` is also required and then unused. `quantity`, `unit_price`, and `discount` are coerced with `errors="coerce"`, but the script does not check for negative quantities or prices, or for discounts outside the 0–1 range.

**Consequence:** A row with an impossible date still passes. A discount greater than 1 would produce a negative `discounted_value` and would still be added into `total_sales`. The required-column check therefore looks stricter than the actual data checks.

**Proposal:** Parse dates in one place. Validate numeric ranges explicitly. If a column is required only because it exists in the source file, document that; if it is unused, do not treat it as part of the calculation pipeline.

### 10. Return rate can divide by zero, and empty data is untested

**Observation:** Both category and region reports calculate `return_rate` as `returns / order_count`. There is no guard for a zero denominator. `order_count` is `order_id.nunique()`, so a group whose order IDs were all missing would have `order_count == 0`. For an empty input file, `unit_price.median()` is `NaN`, and filling missing prices with that median leaves `NaN` in `order_value`.

**Consequence:** The current 80-row file hides these cases. A later empty file or a file with blank order IDs could write `inf` or `NaN` into the reports, or produce a sales total that is not a number, without a clear failure.

**Proposal:** Decide how empty input should be handled, then implement that rule once. When computing rates, treat a zero order count as a defined value such as 0 or “not available”, rather than dividing blindly.

### 11. There is no configuration object

**Observation:** Behavioural settings are scattered through the script as literals: the two file paths, the fill values `"Unknown"`, `1`, `0`, and `"false"`, the accepted return tokens `["true", "yes", "1", "ja"]`, sales rounding to 2 decimals, return-rate rounding to 3 decimals, and the output file names.

**Consequence:** Changing an input path, a rounding rule, or the meaning of a return flag requires editing several lines inside the processing block. Those settings cannot be reused by tests or by a later command-line interface.

**Proposal:** Collect paths, fill rules, rounding, and output file names in one configuration object or module, and pass that object into the processing functions.

### 12. Unclear variable names

**Observation:** The two main aggregated frames are called `result1` and `result2`. The loaded table is called `data`.

**Consequence:** `result1` and `result2` do not say what they contain, so a reader has to compare the `groupby` columns to tell them apart. The generic name `data` also does not show that the frame is the cleaned order table used for every later calculation.

**Proposal:** Use names that describe the contents, such as `sales_by_category`, `sales_by_region`, and `orders`.

### 13. There are no reusable functions and no automated tests

**Observation:** The repository has no `tests` directory and no test files. The script defines no functions that a test could call with a small in-memory DataFrame. Checking a result today means running the whole file against `data/orders.csv` and reading the printed text plus the four CSV files.

**Consequence:** The baseline values above can only be confirmed by hand. A later refactor could change `total_sales`, a return rate, or the `Unknown` region row without any test noticing. The silent cleaning rules are especially easy to break because they are not named or tested.

**Proposal:** After the logic is moved into functions, add tests that reuse the baseline figures from this run (total sales 138036.05, 80 orders, 15 returns, and the category and region tables) and that cover the known dirty rows in `data/orders.csv`.
