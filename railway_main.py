#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DearCraveBreaker Telegram Bot - Railway Optimized Entry Point
Simplified version specifically for Railway deployment
"""

import asyncio
import logging
import os
import threading
import time
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
app = Flask(__name__)

# Global variables
bot_instance = None

@app.route('/')
def health_check():
    """Simple health check for Railway"""
    return {
        'status': 'healthy',
        'service': 'DearCraveBreaker',
        'platform': 'Railway',
        'timestamp': time.time()
    }

@app.route('/ping')
def ping():
    return "pong"

def start_telegram_bot():
    """Start telegram bot in background"""
    try:
        token = os.getenv('PRODUCTION_TELEGRAM_BOT_TOKEN')
        if not token:
            logger.warning("No PRODUCTION_TELEGRAM_BOT_TOKEN found")
            return
            
        # Import and start bot
        from simple_bot import SimpleDearCraveBreakerBot
        global bot_instance
        
        bot_instance = SimpleDearCraveBreakerBot()
        asyncio.run(bot_instance.run())
        
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")

if __name__ == "__main__":
    # Get port from Railway
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"Starting DearCraveBreaker on Railway, port {port}")
    
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask server for health checks
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)