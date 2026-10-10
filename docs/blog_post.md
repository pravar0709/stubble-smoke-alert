# Building an Air Quality Early Warning System for Delhi Schools with AWS

*A hackathon build for the Environmental Hacks track at AWS Bharat Builds Tour*

---

## The Problem That Hits Every Autumn

If you've lived in Delhi during October-November, you know the drill. The air turns grey, your eyes sting, and news channels flash alarming AQI numbers. This is stubble burning season — farmers in Punjab and Haryana clear their fields by setting crop residue on fire, and prevailing northwesterly winds carry the smoke straight into Delhi.

For adults, it's unpleasant. For school children — especially those with asthma or respiratory conditions — it's dangerous.

The frustrating part? Schools often get no advance warning. By the time a CPCB bulletin is published or parents start calling, children have already spent their morning assembly, PE period, or recess breathing hazardous air.

**We wanted to change that. What if schools could know tomorrow's air quality tonight, with a clear instruction on what to do?**

## What We Built

**Stubble Smoke Alert** is a next-day AQI forecasting tool that:

1. **Pulls satellite fire data** from NASA FIRMS — these are real fire detections from the VIIRS sensor at 375-meter resolution
2. **Checks the wind** — if fires are northwest of Delhi and the wind blows from the northwest, that smoke is heading for the city
3. **Predicts tomorrow's AQI band** using a machine learning model trained on historical weather and fire patterns
4. **Translates the prediction into a school action** — not "AQI is 285" (meaningless to a vice principal) but "Move PE and assembly indoors. Keep windows closed."

### The Geospatial Trick

The key insight is that not all fires matter equally. A fire 150km northwest of Delhi on a day with 20 km/h northwesterly winds is far more dangerous than a fire 400km to the south.

We compute this using:
- **Haversine distance**: How far is each fire from Delhi?
- **Bearing**: What direction is the fire relative to Delhi?
- **Upwind weighting**: How closely does the fire's direction match the wind direction?

All implemented in pure numpy — no heavy GIS libraries. The fire detections get binned into distance rings (0-200km, 200-400km) and weighted by how "upwind" they are.

### Being Honest About Model Performance

Here's something we could have hidden but didn't: our model (69.7% accuracy) doesn't beat the naive baseline of "tomorrow's AQI equals today's" (79.4%).

Why? Because AQI has extremely high day-to-day autocorrelation. If today's AQI is 280, there's a very good chance tomorrow's is somewhere around 280 too.

But here's why the model still matters:
- It achieves **96% recall on "Very Poor" days** — the most safety-critical category
- It can detect **transitions** — when AQI is about to jump from Moderate to Severe
- The **policy layer adds value regardless** of model accuracy, by converting any prediction into a bounded action

We report all of this in the UI itself. No black boxes.

## The AWS Architecture

We kept it deliberately simple:

- **Amazon S3**: Stores the forecast JSON, fire detection data, and hosts the static frontend. One bucket, three jobs.
- **AWS Lambda**: A tiny Python function (128MB) that reads pre-computed JSON from S3 and serves it via API. No ML dependencies in Lambda — the heavy lifting happens offline.
- **API Gateway HTTP API**: Routes GET /forecast and GET /fires to Lambda, with CORS for the frontend.
- **AWS SAM**: The entire infrastructure is defined in a single `template.yaml`. One `sam deploy` to recreate everything.

Total cost at hackathon scale: effectively zero. Lambda's free tier covers the first million requests per month, and S3 storage for a few JSON files is fractions of a cent.

## What I Learned

1. **The baseline is your friend, not your enemy.** Reporting that your model doesn't beat a naive baseline isn't failure — it's honesty. And it forces you to articulate *why* your system still adds value (the policy layer, the fire map, the transition detection).

2. **Keep Lambda light.** Our initial instinct was to run the ML model inside Lambda. Bad idea — scikit-learn adds significant cold start time. Instead, we pre-compute the forecast offline and Lambda just reads JSON from S3. Sub-100ms response times.

3. **Policy layers should be independent.** The rule mapping from AQI bands to school actions has zero ML dependencies. It's a pure function with 21 unit tests. If the model is wrong, the policy layer still produces a valid, bounded action.

4. **One feature that runs beats five that almost do.** We scoped aggressively. No user accounts, no historical dashboards, no multi-city support. Just: tomorrow's forecast, the action, the map, the reason. Done.

## Try It

The code is open source. To run it locally:

```bash
pip install -r requirements.txt
python data/download_weather.py
python data/generate_synthetic_aqi.py
python -m src.forecast
python -m http.server 8080 --directory frontend
```

For real fire data, get a free MAP_KEY from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) and add it to your `.env`.

---

*Built at the AWS Bharat Builds Tour hackathon. If you're working on environmental tools for Indian cities, I'd love to hear from you.*
