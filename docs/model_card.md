# Model card — ReefAhead 1.0

## Intended use and target
Research prototype for patrol preparation in the Semporna sea area. Predicts the NOAA CRW fixed-pixel DHW value exactly 7 or 14 days after the issue date. Units: degree C-weeks. It does not classify coral photographs, predict confirmed bleaching, identify coral species, or estimate avoided damage.

## Data and geography
34,744 daily site rows, 2003-01-01 to 2026-10-12. Four 0.05-degree demonstration water pixels; these are not verified reef or dive-site boundaries. No regional moving-maximum sequence is merged into this model.

## Features and physical baseline
Current and lagged SST, HotSpot, anomaly and DHW; past-only rolling moments; seasonal sine/cosine; latitude/longitude; 84-day heat-stress accounting. Only HotSpot >=1 degree C contributes. Physical persistence subtracts the oldest days that leave the 84-day window and assumes current HotSpot persists through the forecast horizon. Anchoring to official DHW tolerates rounding. The residual AI point prediction is floored at max(0, current DHW minus outgoing heat stress minus a fixed precision tolerance). The tolerance is 0.01 + h*0.005/7 degree C-weeks: 0.015 for 7 days and 0.02 for 14 days, fixed before any evaluation. It assumes nearest-0.01 quantization of DHW and HotSpot; ERDDAP metadata expose floats and do not prove the original rounding rule. This retained-stress plausibility floor is not a complete conservation law. Baselines and symmetric interval endpoints are unchanged. Negative official HotSpot values remain features but contribute zero accumulated stress.

## Training and selection
Training: 2003–2016; selection: 2017–2019; refit: 2003–2019; calibration: 2020–2021; locked test: 2022–2025; retrospective forward replay: 2026. Every partition excludes issue dates with target dates beyond its end. Two predeclared residual learners (histogram gradient boosting and random forest) compete against DHW persistence, physical persistence, and training-only seasonal climatology by pooled validation MAE. No test-based tuning, feature selection or retraining. Final fit uses labels only through 2019, including selection years.

## Calibration and events
Per-site 90% symmetric absolute-error calibration uses only 2020–2021 errors; intervals are clipped at zero. Temporal dependence prevents an unconditional exchangeability guarantee. Test coverage is reported. The empirical residual CDF estimates frequency of future satellite DHW>=4, not a validated probability of biological bleaching. Exact-lead threshold crossings are counted separately from strongly autocorrelated event days.

## Reproducibility
Seed 42; Python 3.14.7; scikit-learn 1.9.1; data SHA-256 `b795ba20b11420ed42d29c8525af1ce63c2c4cd606d3a80074030998b42c1062`. Fixed models never use test or 2026 labels for training or calibration.

Model artifact hashes and pipeline source hashes are published in `artifacts/evaluation.json`; the pre-evaluation model-selection protocol and source hashes are in `evidence/training_protocol.json`.

## Limitations
- Four nearby demonstration water pixels; no verified reef geometry, field bleaching labels or independent spatial validation.
- Archives were downloaded retrospectively; issue dates assume same-day inputs, not verified operational availability.
- Autocorrelated temporal calibration does not guarantee 90% future coverage; observed test coverage is reported.
- DHW>=4 is a thermal-stress indicator, not an official Bleaching Alert Area category or proof of bleaching.
- Forecasts require 84 uninterrupted input days; no interpolation or future climate covariates.
- Four sites and daily horizons are correlated; row count is not independent sample size.
- Extreme warming beyond training conditions can invalidate residual corrections and intervals; physical-baseline residual trees do not guarantee extrapolation to unprecedented events.

## Operational guardrails
Issue date is the input observation date, not a verified product release time. Late or missing input must prevent a current operational claim. The API emits input_age_days and stale_input. Historic archives may be revised. This remains a retrospective hindcast until prospective release-time logs and field observations are collected. A human selects patrol actions. These heat-stress signals do not authorize protected-site access or reef intervention.

## Primary source
NOAA CRW DHW definition and risk context: https://coralreefwatch.noaa.gov/product/5km/index_5km_dhw.php
See the project data provenance and manifest for retrieval URLs, licensing and citation information.

## Post-evaluation interpretation

The 7-day validation winner is physical persistence; its reported selected-model performance is not an AI gain. The 14-day winner is the random-forest residual model.

On the 2022–2025 test set, exact-lead first crossings of satellite DHW=4 were detected in 2/3 cases at 7 days and 0/3 at 14 days. These are three correlated pixel-level upcrossings, all in 2024-05, not three independent ecological events. Event-day recall includes already-ongoing stress and must not be presented as evidence of new-event early-warning skill.

For the 14-day forecast, MAE is 0.142168 versus 0.161956 for physical persistence (12.22% lower), but its descriptive block-bootstrap improvement interval [-0.003064, 0.042833] includes zero. False-positive pixel-days fall from 94 to 3, while false negatives rise from 10 to 29; heat-stress-day MAE increases from 0.440913 to 0.487346. There is no established universal superiority.

Nominal 90% intervals cover 88.89% and 89.03% of 7-/14-day test labels; 14-day coverage is 86.35% in the 2026 retrospective replay. These are empirical findings, not coverage guarantees.

In the 2026 replay, 14-day selected-model MAE is 0.183706, worse than the physical baseline (0.167264); the 2022–2025 average improvement does not establish future superiority.

See [complete interpretation, onset cases and annual results](evaluation_analysis.md). Rebuild this section after training with `.venv/bin/python scripts/write_evaluation_analysis.py`; this postprocessor leaves the frozen training source and model artifacts unchanged.
