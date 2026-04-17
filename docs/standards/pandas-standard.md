# pandas Standard: Tabular Analytics, Data Contracts, and Explicit State

## Overview

This document defines how to use **pandas** in this repository for tabular analytics
transformations, feature shaping, and deterministic intermediate computations.

pandas is the canonical dataframe layer for analytics preparation. Usage must remain explicit,
typed where practical, and aligned with fail-fast repository behavior.

## Why pandas

- Strong dataframe and time-series tooling.
- Rich grouping, windowing, and reshaping APIs.
- Tight interoperability with NumPy/SciPy.
- Mature testing utilities for deterministic table assertions.

## Scope

Applies to:

- analytics tabular transforms prior to API serialization
- metric preparation for chart-ready payloads
- deterministic data-validation and test fixtures

Does not apply to:

- ledger truth mutation and accounting policy enforcement
- ad hoc notebook-only logic without production tests

## Installation and Dependency Policy

Use repository-managed dependencies and lockfiles:

```bash
uv add pandas
```

Notes:

- Keep pandas versions pinned through `pyproject.toml` and `uv.lock`.
- Optional extras (`performance`, `computation`, `excel`, `parquet`, etc.) must be added only when
  directly required by accepted scope.

## Core Usage Rules

### 1. Avoid chained assignment; use explicit indexers

- Under Copy-on-Write behavior, chained assignment patterns are not valid update semantics.
- Use `.loc[row_selector, col_selector] = value` for explicit assignment intent.

### 2. Make missing-data behavior explicit

- Use `isna`, `notna`, `fillna`, and `dropna` intentionally.
- Do not infer business semantics from implicit NaN propagation.
- Document null-handling choices for KPI paths.

### 3. Use explicit dtypes for contract-sensitive columns

- Set dtypes deliberately for IDs, quantities, dates, and numeric fields.
- Prefer nullable pandas dtypes where nullability is part of contract semantics.
- Avoid silent mixed-type object columns in production paths.

### 4. Keep large-data operations bounded

- Restrict ingest columns early (for example, `usecols`).
- Filter rows early and avoid unnecessary full-table materialization.
- Convert repeated categorical-like strings to `category` when memory behavior justifies it.

### 5. Keep option changes local

- Use `pd.option_context(...)` for temporary display/behavior tuning.
- Avoid global `pd.set_option(...)` side effects in request-handling code paths.

## Operations-First Workflow for Finance Data

Apply these steps in order before any finance metric calculation:

### 1. Enforce index and ordering invariants

- Ensure time keys are timezone-aware and normalized to one canonical timezone policy.
- Sort by calculation keys before time-aware operations (`resample`, `rolling` on offset windows,
  `merge_asof`).
- Treat unsorted time-series input as a validation failure in estimator paths.

### 2. Lock missing-data policy before math

- Define whether missing values are dropped, forward-filled, or left as null per metric.
- Do not rely on default missing-data propagation for business semantics.
- Record the policy in code comments for contract-facing metrics.

### 3. Lock frequency and business-calendar policy

- Use explicit frequency conversion (`resample`) and, where needed, business-day ranges
  (`bdate_range`) or custom business calendars (`CustomBusinessDay`).
- Avoid mixed-frequency calculations without explicit alignment.

### 4. Lock alignment/join policy for event-time data

- Use `merge_asof` for nearest-prior time alignment of asynchronous market events.
- Require explicit `direction` and `tolerance` in event-time joins.
- Fail fast if alignment keys are not sorted or key coverage is insufficient.

### 5. Lock dtype policy before aggregations

- Keep numeric columns numeric (avoid `object` fallback).
- Keep identifier columns as stable string/category types where appropriate.
- Convert dtypes explicitly before compute-heavy paths.

## Finance Calculation Patterns (Approved Methods)

Use these pandas-native method patterns as first-choice building blocks:

| Finance intent | Primary pandas methods |
| --- | --- |
| Period returns | `pct_change(fill_method=None)`, `shift`, `diff` |
| Cumulative performance | `(1 + returns).cumprod()`, `cummax` |
| Rolling volatility | `rolling(window).std(ddof=1)` |
| Rolling covariance/correlation | `rolling(window).cov(...)`, `rolling(window).corr(...)` |
| Exponentially weighted stats | `ewm(...).mean()`, `ewm(...).std()`, `ewm(...).var()` |
| Bar aggregation | `resample(rule).ohlc()` |
| Event-time alignment | `merge_asof(..., direction=..., tolerance=...)` |
| Grouped portfolio analytics | `groupby(...).agg(...)` with named aggregations |

## Canonical Finance Recipes

Use these as repository baseline patterns for finance transforms:

```python
import numpy as np
import pandas as pd

# Simple and log returns
returns = prices.pct_change(fill_method=None)
log_returns = np.log(prices / prices.shift(1))

# Cumulative return path
cum_return = (1 + returns).cumprod() - 1

# Annualized rolling volatility (example: 252 trading days)
vol_252 = returns.rolling(window=252, min_periods=252).std(ddof=1) * np.sqrt(252)

# Drawdown from running peak
drawdown = prices / prices.cummax() - 1

# Rolling beta versus benchmark
beta_252 = (
    returns.rolling(252).cov(benchmark_returns)
    / benchmark_returns.rolling(252).var(ddof=1)
)

# OHLC bar creation from higher-frequency series
ohlc = prices.resample("1D").ohlc()
```

## Performance and Computation Rules (Finance Focus)

- Prefer vectorized column operations over row-wise `apply`.
- Use `groupby().agg(...)`, `rolling`, `resample`, and `ewm` before custom Python loops.
- Use `Rolling.apply(...)` only for metrics not expressible with built-in vectorized methods.
- For very large workloads, evaluate `Rolling.apply(..., raw=True, engine="numba")` only after
  profiling and only when deterministic behavior is preserved.
- Use `DataFrame.eval`/`query` only on trusted expressions; never pass user-controlled expression
  strings.

## Finance Pitfalls and Required Guards

- `pct_change` returns fractional change, not percentage points; multiply by `100` only for display.
- `merge_asof` requires sorted keys; unsorted input is a correctness defect.
- `resample` and rolling-on-time windows are sensitive to timezone and index frequency choices.
- Chained assignment remains invalid under Copy-on-Write semantics; use explicit `.loc[...]`.
- Do not annualize or compare metrics across mismatched frequencies without explicit conversion.

## Testing Rules (Finance-Focused)

- Assert dataframe outputs with `pandas.testing.assert_frame_equal`.
- Assert series outputs with `pandas.testing.assert_series_equal`.
- Sort/index-normalize before assertions when order is not part of the functional contract.
- Keep timezone handling explicit for datetime columns.
- Use explicit floating tolerances (`rtol`, `atol`) for metric outputs with floating arithmetic.
- Add regression fixtures for canonical metrics (returns, rolling vol, drawdown, beta) so dependency
  upgrades do not silently change outputs.

## Validation Commands

pandas usage quality is validated through repository gates:

```bash
uv run pytest -v
uv run mypy backend scripts
uv run pyright backend scripts
uv run ruff check .
```

## Resources (Official)

- pandas docs index: https://pandas.pydata.org/docs/
- pandas user guide index: https://pandas.pydata.org/docs/user_guide/index.html
- Installation: https://pandas.pydata.org/docs/getting_started/install.html
- Copy-on-Write: https://pandas.pydata.org/docs/user_guide/copy_on_write.html
- Time series / date functionality: https://pandas.pydata.org/docs/user_guide/timeseries.html
- Windowing operations: https://pandas.pydata.org/docs/user_guide/window.html
- Missing data: https://pandas.pydata.org/docs/user_guide/missing_data.html
- Nullable integer dtype: https://pandas.pydata.org/docs/user_guide/integer_na.html
- Scaling to large datasets: https://pandas.pydata.org/docs/user_guide/scale.html
- Options and settings: https://pandas.pydata.org/docs/user_guide/options.html
- Enhancing performance: https://pandas.pydata.org/docs/user_guide/enhancingperf.html
- `DataFrame.pct_change`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html
- `Series.shift`: https://pandas.pydata.org/docs/reference/api/pandas.Series.shift.html
- `DataFrame.rolling`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html
- `DataFrame.ewm`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
- `DataFrame.resample`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.resample.html
- `Resampler.ohlc`: https://pandas.pydata.org/docs/reference/api/pandas.core.resample.Resampler.ohlc.html
- `DataFrame.corr`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corr.html
- `DataFrame.cov`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.cov.html
- `Rolling.apply`: https://pandas.pydata.org/docs/reference/api/pandas.core.window.rolling.Rolling.apply.html
- `merge_asof`: https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html
- `bdate_range`: https://pandas.pydata.org/docs/reference/api/pandas.bdate_range.html
- `CustomBusinessDay`: https://pandas.pydata.org/docs/reference/api/pandas.tseries.offsets.CustomBusinessDay.html
- `assert_frame_equal`: https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html

---

**Last Updated:** 2026-03-28
