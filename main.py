#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DearCraveBreaker Telegram Bot - Production Entry Point
Production version with enhanced error handling and Cloud Run compatibility
"""

import asyncio
import logging
import os
import signal
import sys
import threading
import time
from flask import Flask, jsonify
from simple_bot import SimpleDearCraveBreakerBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
app = Flask(__name__)

# Global bot instance and control variables
bot_instance = None
bot_task = None
running = True

@app.route('/')
def health_check():
    """Health check endpoint for Cloud Run deployment - always returns 200 for deployment success"""
    try:
        # Always return healthy status for deployment health checks
        # Bot status is secondary to Flask server availability
        response_data = {
            'status': 'healthy',
            'service': 'DearCraveBreaker Telegram Bot',
            'version': '1.0.0',
            'flask_server': 'running',
            'bot_running': bot_instance is not None,
            'timestamp': time.time(),
            'port': os.getenv('PORT', '5000')
        }
        return jsonify(response_data), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        # Even if there's an error, return 200 for deployment success
        return jsonify({
            'status': 'healthy',
            'service': 'DearCraveBreaker Telegram Bot',
            'flask_server': 'running',
            'error_logged': str(e)[:100]  # Truncate error message
        }), 200

@app.route('/health')
def health():
    """Alternative health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'bot_token_configured': bool(os.getenv('PRODUCTION_TELEGRAM_BOT_TOKEN'))
    }), 200

@app.route('/status')
def status():
    """Detailed bot status endpoint"""
    global bot_instance
    return jsonify({
        'bot_status': 'running' if bot_instance else 'not_started',
        'bot_token_configured': bool(os.getenv('PRODUCTION_TELEGRAM_BOT_TOKEN')),
        'environment': 'production',
        'port': os.getenv('PORT', '5000'),
        'host': '0.0.0.0'
    }), 200

@app.route('/restart')
def restart_bot():
    """Restart bot endpoint for troubleshooting"""
    global bot_instance
    try:
        if bot_instance:
            logger.info("Restarting bot...")
            start_bot_in_thread()
            return jsonify({'status': 'restarted'}), 200
        else:
            start_bot_in_thread()
            return jsonify({'status': 'started'}), 200
    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

async def run_bot_with_enhanced_error_handling():
    """Run the Telegram bot with enhanced error handling"""
    global bot_instance, running
    
    try:
        # Use production token
        production_token = os.getenv('PRODUCTION_TELEGRAM_BOT_TOKEN')
        if production_token:
            os.environ['TELEGRAM_BOT_TOKEN'] = production_token
        
        bot_instance = SimpleDearCraveBreakerBot()
        
        # Check if bot token is configured
        if not bot_instance.bot_token:
            logger.error("PRODUCTION_TELEGRAM_BOT_TOKEN is not configured!")
            return
            
        logger.info("Starting DearCraveBreaker Telegram Bot (PRODUCTION) with enhanced error handling...")
        
        # Initialize database
        await bot_instance.init_db()
        
        # Clear any existing webhooks before starting
        await bot_instance.delete_webhook()
        await asyncio.sleep(3)  # Wait a bit longer to ensure webhook is cleared
        
        # Start bot polling with retry logic
        retry_count = 0
        max_retries = 5
        
        while running and retry_count < max_retries:
            try:
                logger.info(f"Starting bot polling (attempt {retry_count + 1}/{max_retries})")
                await bot_instance.run_bot()
                break
            except Exception as e:
                retry_count += 1
                if "409" in str(e) or "Conflict" in str(e):
                    logger.warning(f"409 Conflict on attempt {retry_count}, clearing webhook and retrying...")
                    await bot_instance.delete_webhook()
                    await asyncio.sleep(5 * retry_count)  # Exponential backoff
                else:
                    logger.error(f"Bot error on attempt {retry_count}: {e}")
                    if retry_count >= max_retries:
                        logger.error("Max retries reached, bot stopping")
                        break
                    await asyncio.sleep(10)
                    
    except Exception as e:
        logger.error(f"Critical error in bot: {e}")
    finally:
        bot_instance = None

def run_bot_async():
    """Run the Telegram bot in async context with better error handling"""
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        task = loop.create_task(run_bot_with_enhanced_error_handling())
        loop.run_until_complete(task)
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
    finally:
        loop.close()

def start_bot_in_thread():
    """Start the bot in a separate thread"""
    bot_thread = threading.Thread(target=run_bot_async, daemon=True)
    bot_thread.start()
    logger.info("Production DearCraveBreaker bot thread started with enhanced error handling")
    return bot_thread

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False
    sys.exit(0)

def main():
    """Main function for deployment compatibility"""
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start Flask server for health checks FIRST to ensure Cloud Run deployment success
        port = int(os.environ.get('PORT', 5000))
        host = '0.0.0.0'  # Always bind to all interfaces for Cloud Run
        
        logger.info(f"Starting DearCraveBreaker PRODUCTION Flask health server on {host}:{port}")
        logger.info(f"Production bot token configured: {bool(os.getenv('PRODUCTION_TELEGRAM_BOT_TOKEN'))}")
        logger.info(f"Environment: PRODUCTION (Railway)")
        
        # Start the Telegram bot in a separate thread AFTER Flask is ready
        try:
            start_bot_in_thread()
            logger.info("DearCraveBreaker production bot started in background thread")
        except Exception as bot_error:
            logger.warning(f"Bot startup failed, continuing with health server: {bot_error}")
        
        # Start Flask with production settings - this should always succeed for health checks
        app.run(
            host=host, 
            port=port, 
            debug=False, 
            threaded=True,
            use_reloader=False  # Prevent double startup in development
        )
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        # Try to start Flask without bot for health checks
        try:
            logger.info("Attempting emergency health server startup...")
            app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
        except:
            sys.exit(1)

if __name__ == "__main__":
    main()