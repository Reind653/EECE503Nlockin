import json
import logging
import os
import requests
import sys
import psutil
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add metrics helper to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metrics_helper import setup_metrics, track_llm_request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Setup Prometheus metrics
metrics_dict = setup_metrics(app, 'iep2')

# Load environment variables for Anthropic API
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DEFAULT_MODEL = os.getenv('LLM_MODEL', 'claude-3-7-sonnet-20250219')  # Default to Claude 3.7 Sonnet

# Log the configuration
logger.info(f"Using default model: {DEFAULT_MODEL}")

# Periodically update system metrics
@app.before_request
def update_system_metrics():
    process = psutil.Process(os.getpid())
    metrics_dict['system_memory_usage'].labels(service='iep2').set(process.memory_info().rss)

def call_anthropic_api(prompt, model=None, temperature=0.2, max_tokens=4000):
    """
    Pure function to call Anthropic API with a prompt.
    Returns the raw API response.
    """
    start_time = time.time()
    try:
        if not ANTHROPIC_API_KEY:
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/api/generate', error_type='api_key_missing').inc()
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Use provided model or fall back to default
        model_to_use = model or DEFAULT_MODEL
        logger.info(f"Calling Anthropic API with model: {model_to_use}")
        
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Messages API format for Claude models
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Track LLM request metrics
        with track_llm_request(metrics_dict, 'anthropic', model_to_use) as tracker:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60  # Longer timeout for complex requests
            )
            
            # Estimate token usage
            prompt_tokens = len(prompt) / 4  # Rough estimate
            if response.status_code == 200:
                response_data = response.json()
                response_content = response_data.get('content', [{}])[0].get('text', '')
                response_tokens = len(response_content) / 4  # Rough estimate
                tracker.record_tokens(input_tokens=prompt_tokens, output_tokens=response_tokens)
        
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/api/generate', error_type='anthropic_api_error').inc()
            return {"error": f"Anthropic API returned error: {response.status_code} - {response.text}"}, response.status_code
        
        # Return the raw API response
        return response.json(), 200
            
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {str(e)}")
        metrics_dict['api_errors_total'].labels(method='POST', endpoint='/api/generate', error_type='exception').inc()
        return {"error": str(e)}, 500

@app.route('/')
def index():
    """Health check endpoint."""
    start_time = time.time()
    status_code = 200
    try:
        response = {
            "service": "IEP2 - Anthropic API Bridge",
            "status": "active",
            "version": "1.0.0",
            "default_model": DEFAULT_MODEL
        }
        return jsonify(response)
    finally:
        duration = time.time() - start_time
        metrics_dict['api_request_duration'].labels(method='GET', endpoint='/').observe(duration)
        metrics_dict['api_requests_total'].labels(method='GET', endpoint='/', status=status_code).inc()

@app.route('/api/generate', methods=['POST'])
def create_schedule():
    """
    Simple API bridge to Anthropic.
    Takes a prompt and returns the raw API response.
    All business logic is handled by EEP1.
    """
    start_time = time.time()
    status_code = 200
    try:
        data = request.json
        if not data or 'prompt' not in data:
            status_code = 400
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/api/generate', error_type='missing_prompt').inc()
            return jsonify({"error": "No prompt provided"}), status_code
        
        # Extract parameters
        prompt = data['prompt']
        model = data.get('model', DEFAULT_MODEL)
        temperature = data.get('temperature', 0.2)
        max_tokens = data.get('max_tokens', 4000)
        
        logger.info(f"Received prompt for Anthropic API (length: {len(prompt)} chars)")
        
        # Make the API call and return the raw response
        response, status_code = call_anthropic_api(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # If there was an error, return it directly
        if status_code != 200:
            return jsonify(response), status_code
            
        logger.info(f"Successfully called Anthropic API, returning raw response")
        
        # Return the raw API response - let EEP1 handle the parsing
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in API bridge: {str(e)}")
        status_code = 500
        metrics_dict['api_errors_total'].labels(method='POST', endpoint='/api/generate', error_type='server_error').inc()
        return jsonify({"error": str(e)}), status_code
    finally:
        # Record request metrics
        duration = time.time() - start_time
        metrics_dict['api_request_duration'].labels(method='POST', endpoint='/api/generate').observe(duration)
        metrics_dict['api_requests_total'].labels(method='POST', endpoint='/api/generate', status=status_code).inc()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)
