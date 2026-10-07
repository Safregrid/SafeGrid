# SafeGrid — Risk Model

> Status: **PLACEHOLDER — to be filled in by Person 2.**
> Every threshold entry must include: value, meaning, justification, source, and known limitations.

---

## Structure

For each hazard type, document:

1. **Hazard name**
2. **Data source** (e.g. USGS, Open-Meteo)
3. **Input parameter** (e.g. magnitude, precipitation mm/h)
4. **Thresholds**

| Risk level | Condition | Justification | Source | Limitations |
|---|---|---|---|---|
| HIGH | ... | ... | ... | ... |
| MODERATE | ... | ... | ... | ... |
| LOW | ... | ... | ... | ... |

5. **Affected area computation** — describe how the geographic polygon is derived.

---

## Earthquake (USGS) — PLACEHOLDER

> Person 2 must fill this in before implementing risk calculations.

Input: Richter magnitude from USGS feed.

Thresholds: **NOT YET DECIDED.**

Affected area: **NOT YET DECIDED.** Options include fixed-radius buffer (oversimplification) or felt-intensity contours (more accurate but harder). Document the choice and tradeoffs.

---

## Rainfall / Weather (Open-Meteo) — PLACEHOLDER

> Person 2 must fill this in before implementing risk calculations.

Input: precipitation mm/h (or mm/day), relevant Open-Meteo parameter.

Thresholds: **NOT YET DECIDED.**

Affected area: **NOT YET DECIDED.**

---

## General rule

Do not invent thresholds to make the demo look good.
If a threshold cannot be justified with a reference, it must be clearly labelled as a working assumption.

Working assumption format:

> **WORKING ASSUMPTION**: [threshold value].
> Reason: [why this value was chosen].
> Limitation: This is not derived from an authoritative source. It should be replaced before any public use.
