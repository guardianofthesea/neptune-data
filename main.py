import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from models import (
    MarketData, TokenPrices, ContractData, NEPTData, SessionLocal
)
from sqlalchemy import desc
import threading
import time
from collect_data import collect_and_store_data
import schedule
from database import get_db
import os

app = Flask(__name__)

# Get schedule interval from environment variable, default to 30 minutes
SCHEDULE_INTERVAL = int(os.getenv('SCHEDULE_INTERVAL_MINUTES', '30'))

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

# Get the logger
logger = logging.getLogger('neptune-data')

# Ensure the logger has the correct level
logger.setLevel(logging.INFO)

# Add a custom formatter to the logger
formatter = logging.Formatter('%(message)s')
for handler in logger.handlers:
    handler.setFormatter(formatter)

# Global variables for health check
collection_thread = None

def start_background_tasks():
    global collection_thread
    try:
        # Start data collection thread
        logger.info("Starting background tasks thread for data collection")
        
        # Get the last entry time from the database
        db = SessionLocal()
        try:
            latest_market_data = db.query(MarketData).order_by(desc(MarketData.timestamp)).first()
            if latest_market_data:
                # Calculate time until next scheduled run
                last_run = latest_market_data.timestamp
                next_run = last_run + timedelta(minutes=SCHEDULE_INTERVAL)
                now = datetime.utcnow()
                
                if next_run > now:
                    # Schedule for the calculated next run time
                    delay = (next_run - now).total_seconds()
                    logger.info(f"Last data collection was at {last_run}, scheduling next run in {delay/60:.1f} minutes")
                    schedule.every(delay).seconds.do(job)
                else:
                    # Run immediately if we're past the scheduled time
                    logger.info("Last data collection is older than schedule interval, running immediately")
                    job()
            else:
                # No previous data, run immediately
                logger.info("No previous data found, running immediately")
                job()
            
            # Schedule subsequent runs
            schedule.every(SCHEDULE_INTERVAL).minutes.do(job)
            logger.info(f"Scheduled data collection to run every {SCHEDULE_INTERVAL} minutes")
            
        finally:
            db.close()
        
        # Start scheduler in a separate thread
        collection_thread = threading.Thread(target=run_scheduler)
        collection_thread.daemon = True
        collection_thread.start()
            
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Failed to start background tasks: {str(e)}", exc_info=True)
        raise

@app.route('/')
def index():
    """Get the latest data from all categories"""
    logger.info("Received request for latest data")
    db = SessionLocal()
    try:
        latest_data = {
            'market_data': db.query(MarketData).order_by(desc(MarketData.timestamp)).first(),
            'price_data': db.query(TokenPrices).order_by(desc(TokenPrices.timestamp)).first(),
            'contract_data': db.query(ContractData).order_by(desc(ContractData.timestamp)).first(),
            'nept_data': db.query(NEPTData).order_by(desc(NEPTData.timestamp)).first()
        }
        logger.info(f"Returning latest data: {latest_data}")
        return jsonify({
            k: v.__dict__ if v else None 
            for k, v in latest_data.items()
        })
    finally:
        db.close()

@app.route('/historical/<data_type>/<int:days>')
def historical_data(data_type, days):
    """Get historical data for a specific type over a number of days"""
    logger.info(f"Received request for historical {data_type} data for {days} days")
    db = SessionLocal()
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        model_map = {
            'market': MarketData,
            'price': TokenPrices,
            'contract': ContractData,
            'nept': NEPTData
        }
        
        if data_type not in model_map:
            return jsonify({'error': 'Invalid data type'}), 400
            
        model = model_map[data_type]
        data = db.query(model).filter(
            model.timestamp >= start_date,
            model.timestamp <= end_date
        ).order_by(model.timestamp).all()
        
        logger.info(f"Returning {len(data)} historical records")
        return jsonify([item.__dict__ for item in data])
    finally:
        db.close()

@app.route('/health')
def health():
    logger.info("Health check requested")
    db = SessionLocal()
    try:
        latest_market_data = db.query(MarketData).order_by(desc(MarketData.timestamp)).first()
        status = {
            'status': 'healthy',
            'last_update': latest_market_data.timestamp.isoformat() if latest_market_data else None,
            'data_available': bool(latest_market_data),
            'collection_thread_running': bool(collection_thread and collection_thread.is_alive())
        }
        logger.info(f"Health check status: {status}")
        return jsonify(status)
    finally:
        db.close()

async def run_collection():
    logger.info(f"Starting data collection at {datetime.utcnow()}")
    await collect_and_store_data()

def job():
    asyncio.run(run_collection())

def run_scheduler():
    """Run the scheduler in a separate thread"""
    logger.info("Starting scheduler thread")
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start background tasks when the application starts
start_background_tasks()

if __name__ == "__main__":
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080)
