"""
Nepal EBS - Signal Detection Module
Detects health hazard signals from news articles using keyword matching.
"""
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict


class SignalDetector:
    """Detects health hazard signals from news articles."""
    
    def __init__(self, keywords_file='data/keywords.json'):
        with open(keywords_file, 'r', encoding='utf-8') as f:
            self.keywords = json.load(f)
        
        # Compile keyword patterns for efficient matching
        self.hazard_patterns = {}
        for hazard_type, words in self.keywords['hazards'].items():
            all_words = words['en'] + words['ne']
            self.hazard_patterns[hazard_type] = [
                re.compile(r'\b' + re.escape(w.lower()) + r'\b', re.IGNORECASE)
                for w in all_words
            ]
        
        self.location_patterns = [
            re.compile(r'\b' + re.escape(w.lower()) + r'\b', re.IGNORECASE)
            for w in self.keywords['location_indicators']['en'] + self.keywords['location_indicators']['ne']
        ]
        
        self.severity_patterns = [
            re.compile(r'\b' + re.escape(w.lower()) + r'\b', re.IGNORECASE)
            for w in self.keywords['severity_boosters']['en'] + self.keywords['severity_boosters']['ne']
        ]
    
    def detect_hazards(self, text):
        """Detect hazard types in text."""
        text_lower = text.lower()
        detected = {}
        
        for hazard_type, patterns in self.hazard_patterns.items():
            matches = []
            for p in patterns:
                found = p.findall(text_lower)
                matches.extend(found)
            if matches:
                detected[hazard_type] = list(set(matches))
        
        return detected
    
    def detect_severity_boosters(self, text):
        """Detect severity booster words in text."""
        text_lower = text.lower()
        matches = []
        for pattern in self.severity_patterns:
            found = pattern.findall(text_lower)
            matches.extend(found)
        return list(set(matches))
    
    def calculate_score(self, hazards, severity_boosters, has_location):
        """Calculate signal score based on detected features."""
        score = 0
        
        # Base score for hazard detection
        score += len(hazards) * 2
        
        # Bonus for multiple hazard types
        if len(hazards) >= 2:
            score += 3
        
        # Bonus for severity boosters
        score += len(severity_boosters) * 1.5
        
        # Bonus for location mention
        if has_location:
            score += 2
        
        # Bonus for outbreak + location combination
        if 'waterborne_outbreak' in hazards and has_location:
            score += 3
        
        return min(score, 10)  # Cap at 10
    
    def classify_signal(self, score):
        """Classify signal based on score."""
        if score >= 8:
            return 'critical'
        elif score >= 6:
            return 'high'
        elif score >= 4:
            return 'medium'
        else:
            return 'low'
    
    def analyze_article(self, article):
        """Analyze a single article for health hazard signals."""
        text = f"{article.get('title', '')} {article.get('content', '')}"
        
        hazards = self.detect_hazards(text)
        severity_boosters = self.detect_severity_boosters(text)
        has_location = any(p.search(text.lower()) for p in self.location_patterns)
        
        score = self.calculate_score(hazards, severity_boosters, has_location)
        severity = self.classify_signal(score)
        
        return {
            'article': article,
            'hazards': hazards,
            'severity_boosters': severity_boosters,
            'has_location': has_location,
            'score': score,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_articles(self, articles):
        """Analyze multiple articles and return signals."""
        signals = []
        for article in articles:
            signal = self.analyze_article(article)
            if signal['hazards']:  # Only include if hazards detected
                signals.append(signal)
        
        # Sort by score descending
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals


class Deduplicator:
    """Deduplicate similar signals."""
    
    def __init__(self, time_window_hours=48):
        self.time_window = timedelta(hours=time_window_hours)
    
    def is_duplicate(self, signal, existing_signals):
        """Check if a signal is a duplicate of an existing one."""
        article = signal['article']
        article_time = article.get('published', datetime.now())
        
        for existing in existing_signals:
            existing_article = existing['article']
            existing_time = existing_article.get('published', datetime.now())
            
            # Ensure both datetimes are naive for comparison
            if article_time.tzinfo is not None:
                article_time = article_time.replace(tzinfo=None)
            if existing_time.tzinfo is not None:
                existing_time = existing_time.replace(tzinfo=None)
            
            # Check time window
            if abs((article_time - existing_time).total_seconds()) > self.time_window.total_seconds():
                continue
            
            # Check if same hazards
            if set(signal['hazards'].keys()) != set(existing['hazards'].keys()):
                continue
            
            # Check title similarity (simple)
            if self._title_similarity(article.get('title', ''), existing_article.get('title', '')) > 0.6:
                return True
        
        return False
    
    def _title_similarity(self, title1, title2):
        """Calculate simple title similarity."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def deduplicate(self, signals):
        """Remove duplicate signals."""
        unique_signals = []
        
        for signal in signals:
            if not self.is_duplicate(signal, unique_signals):
                unique_signals.append(signal)
        
        return unique_signals


if __name__ == '__main__':
    from scraper import get_demo_articles
    
    detector = SignalDetector()
    articles = get_demo_articles()
    signals = detector.analyze_articles(articles)
    
    print(f"Detected {len(signals)} signals from {len(articles)} articles:")
    for s in signals:
        print(f"  [{s['severity'].upper()}] Score: {s['score']:.1f} - {s['article']['title'][:50]}...")
        print(f"    Hazards: {list(s['hazards'].keys())}")
