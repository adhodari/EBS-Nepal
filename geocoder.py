"""
Nepal EBS - Geocoding Module
Extracts location information from text and maps to coordinates.
"""
import json
import re


class Geocoder:
    """Geocodes location mentions in text to coordinates."""
    
    def __init__(self, municipalities_file='data/municipalities.json'):
        with open(municipalities_file, 'r', encoding='utf-8') as f:
            self.municipalities = json.load(f)
        
        # Build lookup indexes
        self.name_index = {}
        self.ne_name_index = {}
        
        for m in self.municipalities:
            # Index by English name (lowercase)
            self.name_index[m['name'].lower()] = m
            # Index by Nepali name
            self.ne_name_index[m['ne']] = m
            # Index by district
            self.name_index[m['district'].lower()] = m
            # Index by province
            self.name_index[m['province'].lower()] = m
    
    def extract_locations(self, text):
        """Extract location mentions from text."""
        text_lower = text.lower()
        found_locations = []
        
        for name, municipality in self.name_index.items():
            if name in text_lower:
                found_locations.append(municipality)
        
        # Check Nepali names
        for name, municipality in self.ne_name_index.items():
            if name in text:
                found_locations.append(municipality)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_locations = []
        for loc in found_locations:
            key = loc['name']
            if key not in seen:
                seen.add(key)
                unique_locations.append(loc)
        
        return unique_locations
    
    def geocode_article(self, article):
        """Geocode an article and add location data."""
        text = f"{article.get('title', '')} {article.get('content', '')}"
        locations = self.extract_locations(text)
        
        return {
            'article': article,
            'locations': locations,
            'primary_location': locations[0] if locations else None
        }
    
    def geocode_signals(self, signals):
        """Geocode multiple signals."""
        geocoded = []
        for signal in signals:
            result = self.geocode_article(signal['article'])
            signal['locations'] = result['locations']
            signal['primary_location'] = result['primary_location']
            geocoded.append(signal)
        return geocoded


if __name__ == '__main__':
    from scraper import get_demo_articles
    
    geocoder = Geocoder()
    articles = get_demo_articles()
    
    for article in articles[:3]:
        result = geocoder.geocode_article(article)
        print(f"Title: {article['title'][:50]}...")
        print(f"  Locations found: {[l['name'] for l in result['locations']]}")
        if result['primary_location']:
            print(f"  Primary: {result['primary_location']['name']} ({result['primary_location']['lat']}, {result['primary_location']['lng']})")
        print()
