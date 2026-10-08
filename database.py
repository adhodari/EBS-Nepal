"""
Nepal EBS - Database Module
SQLite-based persistent storage for signals and articles.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path


class Database:
    """SQLite database for persistent signal storage."""
    
    def __init__(self, db_path='data/signals.db'):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                source TEXT,
                published TIMESTAMP,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT,
                score REAL,
                hazards TEXT,
                locations TEXT,
                language TEXT
            )
        ''')
        
        # Articles table (raw scraped data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT UNIQUE,
                source TEXT,
                published TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                language TEXT
            )
        ''')
        
        # Scan history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                articles_found INTEGER,
                signals_detected INTEGER,
                status TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_signal(self, signal):
        """Save a signal to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (title, content, url, source, published, 
                               detected_at, severity, score, hazards, locations, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal['article']['title'],
            signal['article']['content'],
            signal['article']['url'],
            signal['article']['source'],
            signal['article']['published'],
            datetime.now().isoformat(),
            signal['severity'],
            signal['score'],
            json.dumps(signal['hazards']),
            json.dumps(signal.get('locations', [])),
            signal['article'].get('language', 'en')
        ))
        
        conn.commit()
        conn.close()
    
    def save_article(self, article):
        """Save an article to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO articles (title, content, url, source, published, language)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article['content'],
                article['url'],
                article['source'],
                article['published'],
                article.get('language', 'en')
            ))
            conn.commit()
        except Exception as e:
            print(f"Error saving article: {e}")
        finally:
            conn.close()
    
    def save_scan_history(self, started_at, articles_found, signals_detected, status='completed'):
        """Save scan history entry."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scan_history (started_at, completed_at, articles_found, signals_detected, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            started_at.isoformat(),
            datetime.now().isoformat(),
            articles_found,
            signals_detected,
            status
        ))
        
        conn.commit()
        conn.close()
    
    def get_signals(self, limit=100, severity=None, hazard_type=None, 
                    start_date=None, end_date=None):
        """Get signals with optional filters."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM signals WHERE 1=1'
        params = []
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        if hazard_type:
            query += ' AND hazards LIKE ?'
            params.append(f'%"{hazard_type}"%')
        
        if start_date:
            query += ' AND published >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND published <= ?'
            params.append(end_date)
        
        query += ' ORDER BY detected_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        signals = []
        for row in rows:
            signal = dict(row)
            signal['hazards'] = json.loads(signal['hazards'])
            signal['locations'] = json.loads(signal['locations'])
            signals.append(signal)
        
        conn.close()
        return signals
    
    def get_recent_signals(self, hours=48):
        """Get signals from the last N hours."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT * FROM signals 
            WHERE detected_at >= ? 
            ORDER BY detected_at DESC
        ''', (cutoff,))
        
        rows = cursor.fetchall()
        
        signals = []
        for row in rows:
            signal = dict(row)
            signal['hazards'] = json.loads(signal['hazards'])
            signal['locations'] = json.loads(signal['locations'])
            signals.append(signal)
        
        conn.close()
        return signals
    
    def get_stats(self):
        """Get statistics from the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total signals
        cursor.execute('SELECT COUNT(*) FROM signals')
        total_signals = cursor.fetchone()[0]
        
        # By severity
        cursor.execute('''
            SELECT severity, COUNT(*) as count 
            FROM signals 
            GROUP BY severity
        ''')
        by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        # By hazard type
        cursor.execute('SELECT hazards FROM signals')
        by_hazard = {}
        for row in cursor.fetchall():
            hazards = json.loads(row['hazards'])
            for hazard in hazards:
                by_hazard[hazard] = by_hazard.get(hazard, 0) + 1
        
        # By location
        cursor.execute('SELECT locations FROM signals')
        by_location = {}
        for row in cursor.fetchall():
            locations = json.loads(row['locations'])
            for loc in locations:
                name = loc.get('name', 'Unknown')
                by_location[name] = by_location.get(name, 0) + 1
        
        # Recent scans
        cursor.execute('''
            SELECT * FROM scan_history 
            ORDER BY started_at DESC 
            LIMIT 10
        ''')
        recent_scans = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_signals': total_signals,
            'by_severity': by_severity,
            'by_hazard': by_hazard,
            'by_location': by_location,
            'recent_scans': recent_scans
        }
    
    def get_trends(self, days=7):
        """Get signal trends over time."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT DATE(detected_at) as date, severity, COUNT(*) as count
            FROM signals
            WHERE detected_at >= ?
            GROUP BY DATE(detected_at), severity
            ORDER BY date
        ''', (cutoff,))
        
        trends = {}
        for row in cursor.fetchall():
            date = row['date']
            if date not in trends:
                trends[date] = {}
            trends[date][row['severity']] = row['count']
        
        conn.close()
        return trends
    
    def cleanup_old_signals(self, days=30):
        """Remove signals older than specified days."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('DELETE FROM signals WHERE detected_at < ?', (cutoff,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted


if __name__ == '__main__':
    db = Database()
    print("Database initialized successfully")
    print(f"Stats: {db.get_stats()}")
