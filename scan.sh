#!/bin/bash
# Nepal EBS - Automated scan script
# Runs every 8 hours via cron

LOG_FILE="/home/dell/Documents/Default Project/nepal-ebs/scan.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Starting scan..." >> "$LOG_FILE"

# Trigger scan via API
RESULT=$(curl -s -X POST http://localhost:5000/api/scan \
    -H "Content-Type: application/json" \
    -d '{"use_demo": true}')

echo "[$TIMESTAMP] Scan result: $RESULT" >> "$LOG_FILE"

# Get stats
STATS=$(curl -s http://localhost:5000/api/stats)
echo "[$TIMESTAMP] Stats: $STATS" >> "$LOG_FILE"

echo "[$TIMESTAMP] Scan completed." >> "$LOG_FILE"
