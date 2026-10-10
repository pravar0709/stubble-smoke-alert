# 3-Minute Demo Script: Stubble Smoke Alert

## Setup (before demo)
- Have the live URL open in a browser tab
- Have AWS Console open (Lambda, API Gateway, S3)
- Have the terminal ready with the project directory

---

## Slide 1: The Problem (30 seconds)

> "Every autumn, stubble burning in Punjab and Haryana blankets Delhi in toxic smoke.
> AQI regularly crosses 300 — that's 'Severe' on the CPCB scale.
>
> Schools are caught off-guard. By the time they react, kids have already
> been outside for PE and assembly in hazardous air.
>
> **What if schools could get tomorrow's air quality forecast tonight,
> with a clear action they can take?**"

---

## Slide 2: The Solution — Live Demo (60 seconds)

*Switch to browser showing the live URL*

> "This is Stubble Smoke Alert. Let me walk you through what a school
> administrator sees:
>
> 1. **The forecast band** — right here, 'Very Poor', AQI 201-300.
>    Color-coded so it's instantly clear.
>
> 2. **The action** — 'Move PE and assembly indoors. Keep windows closed.'
>    This is a bounded, specific instruction — not a vague warning.
>
> 3. **The reason** — 'Northwesterly winds at 18 km/h carrying smoke
>    toward Delhi.' The administrator knows *why*, not just *what*.
>
> 4. **The fire map** — *scroll down* — these orange dots are real
>    satellite fire detections from NASA VIIRS. The dashed arrow shows
>    wind direction. You can see the fires in Punjab and the smoke
>    path toward Delhi.
>
> 5. **Model transparency** — we show the model accuracy (69.7%)
>    AND the baseline (79.4%) honestly. The value isn't beating a
>    baseline — it's converting a forecast into a school action."

---

## Slide 3: How It Works (45 seconds)

> "Under the hood:
>
> 1. We pull daily weather from Open-Meteo — wind speed, direction,
>    temperature, humidity.
>
> 2. We count satellite fire detections that are *upwind* of Delhi
>    using haversine distance and bearing — all in numpy, no heavy GIS.
>
> 3. A GradientBoosting model predicts tomorrow's AQI band from these
>    features plus today's AQI.
>
> 4. A separate, rule-based policy layer — fully unit-tested, independent
>    of the model — maps the band to a school action.
>
> 5. 64 automated tests cover the geo math, features, policy rules,
>    and API shape."

---

## Slide 4: AWS Architecture (30 seconds)

*Switch to AWS Console*

> "The entire backend runs on AWS:
>
> - **S3** *[click to S3 bucket]* — stores the forecast JSON, fire data,
>   and hosts the static frontend. Zero servers.
>
> - **Lambda** *[click to Lambda function]* — a tiny Python function that
>   reads from S3 and serves GET /forecast and GET /fires. 128MB, <100ms.
>
> - **API Gateway** *[click to API Gateway]* — HTTP API with CORS,
>   routes to Lambda. Auto-scaling, pay-per-request.
>
> - **SAM template** — one `sam deploy` to reproduce everything.
>
> Total monthly cost: effectively zero at hackathon scale."

---

## Slide 5: Impact & Next Steps (15 seconds)

> "With real CPCB data and a FIRMS API key, this becomes a production
> early-warning system. Add EventBridge for daily automated updates
> and SNS for email alerts to schools.
>
> One feature that runs beats five that almost do.
> Thank you."

---

## Backup Q&A Points

- **Why does the baseline beat the model?** AQI has high autocorrelation.
  Tomorrow usually equals today. Our value is in catching transitions
  and converting predictions into bounded actions.

- **Is the data real?** Weather is real (Open-Meteo). AQI is synthetic
  (calibrated to Delhi patterns). Fire data requires a free NASA key.
  Real data drops in with zero code changes.

- **What about false alarms?** The policy layer is conservative —
  a false "Very Poor" means kids stay inside unnecessarily (safe),
  while a missed "Severe" is dangerous. We bias toward safety.
