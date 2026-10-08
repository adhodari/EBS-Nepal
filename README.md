# Nepal EBS - Event-Based Surveillance Tool

A web-based tool for monitoring health hazards in Nepal through news media analysis. This tool implements Event-Based Surveillance (EBS) by scraping Nepali news portals, detecting health hazard signals using bilingual keyword matching, geocoding locations, and visualizing results on an interactive map.

## Features

- **News Scraping**: Collects articles from major Nepali news portals (RSS feeds)
- **Bilingual Detection**: Detects health hazards in both English and Nepali
- **Geocoding**: Maps location mentions to coordinates using municipality database
- **Signal Scoring**: Prioritizes signals based on severity and context
- **Deduplication**: Groups similar reports to avoid duplicate alerts
- **Interactive Dashboard**: Visualizes signals on a map with filtering capabilities

## Project Structure

```
nepal-ebs/
├── app.py                 # Flask web application
├── scraper.py             # News scraping module
├── detector.py            # Signal detection and scoring
├── geocoder.py            # Location extraction and geocoding
├── data/
│   ├── municipalities.json # Nepal municipalities with coordinates
│   └── keywords.json      # Bilingual keyword matrix
├── templates/
│   └── index.html         # Dashboard template
├── static/
│   └── style.css          # Dashboard styles
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Installation

1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. The dashboard will automatically load with demo data

4. Click "Run Scan" to fetch and analyze news articles

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/signals` - Get all detected signals (with optional filters)
- `GET /api/signals/<id>` - Get specific signal details
- `POST /api/scan` - Trigger a new scan
- `GET /api/stats` - Get statistics
- `GET /api/municipalities` - Get municipality data

## Signal Severity Levels

- **Critical** (Score 8-10): Outbreak + location + severity boosters
- **High** (Score 6-7): Multiple hazards or hazard + location
- **Medium** (Score 4-5): Single hazard with some context
- **Low** (Score 1-3): Single hazard mention

## Hazard Types

- Water Contamination
- Waterborne Outbreak (Cholera, Diarrhea, Typhoid)
- Vector Borne (Dengue, Malaria)
- Environmental Triggers (Flood, Landslide)
- Respiratory (Pneumonia, Flu)
- Foodborne (Food poisoning)

## Customization

### Adding News Sources
Edit `scraper.py` to add more RSS feeds:
```python
NEWS_SOURCES = [
    {
        "name": "Your Source",
        "url": "https://example.com/rss",
        "type": "rss",
        "language": "en",  # or "ne"
        "priority": 1
    }
]
```

### Updating Keywords
Edit `data/keywords.json` to add or modify detection keywords.

### Adding Municipalities
Edit `data/municipalities.json` to add more locations with coordinates.

## Important Notes

- This tool uses demo data by default for demonstration purposes
- Live scraping may be blocked by some news sites
- The tool is a supplementary early warning system, not a replacement for official surveillance
- Media bias toward urban centers may affect detection in rural areas
- News reports are lagging indicators compared to actual disease surveillance

## License

MIT License - Free for use and modification.
