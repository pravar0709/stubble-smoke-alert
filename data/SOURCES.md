# Data Sources and Licences

## 1. Open-Meteo Historical Weather API
- **URL**: https://open-meteo.com/
- **Data**: ERA5 reanalysis (ECMWF), daily wind/temperature/humidity for Delhi
- **Licence**: CC BY 4.0 (Attribution)
- **Key required**: No
- **Limitations**: ~5-month lag for recent data; uses reanalysis, not station obs.

## 2. NASA FIRMS (Fire Information for Resource Management System)
- **URL**: https://firms.modaps.eosdis.nasa.gov/
- **Data**: VIIRS S-NPP active fire detections (375m resolution)
- **Licence**: Open data, free for all users. Citation requested.
- **Key required**: Yes — free MAP_KEY from https://firms.modaps.eosdis.nasa.gov/api/
- **Limitations**: Cloud cover can mask fires. NRT data may have false positives.
- **Citation**: NASA FIRMS. Fire Information for Resource Management System (FIRMS).
  doi:10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002

## 3. Delhi AQI Data
- **Primary**: CPCB (Central Pollution Control Board) daily AQI bulletins
- **Alternative sources**:
  - OpenAQ (https://openaq.org/) — harmonised CPCB station data
  - Kaggle community datasets (https://www.kaggle.com/)
  - UrbanEmissions.info — curated India air quality data
- **Licence**: CPCB data is public. OpenAQ data is CC BY 4.0.
- **Fallback**: Synthetic data (`delhi_aqi_synthetic.csv`) is generated when
  no real CSV is available. It follows known Delhi seasonal AQI patterns but
  is NOT real measurement data.

## Notes
- All raw data files are excluded from git via `.gitignore`.
- Synthetic data is clearly labeled with a `source` column = "synthetic".
- The model's README and UI both disclose when synthetic data is used.
