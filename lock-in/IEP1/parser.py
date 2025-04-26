import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import logging
import json
import traceback
import sys
import psutil
import time

# Add metrics helper to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metrics_helper import setup_metrics, track_llm_request

# ----------------------------------------------
# Initialization and Setup
# ----------------------------------------------

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Setup Prometheus metrics
metrics_dict = setup_metrics(app, 'iep1')

# Check if API key is available
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set!")
else:
    logger.info("OPENAI_API_KEY environment variable is set")

# Create OpenAI client
client = OpenAI(api_key=api_key)
logger.debug("OpenAI client configured")

# Periodically update system metrics
@app.before_request
def update_system_metrics():
    process = psutil.Process(os.getpid())
    metrics_dict['system_memory_usage'].labels(service='iep1').set(process.memory_info().rss)

# ----------------------------------------------
# Prediction Endpoint
# ----------------------------------------------

@app.route('/predict', methods=['POST'])
def predict():
    start_time = time.time()
    status_code = 200
    try:
        data = request.json
        logger.debug(f"Received data: {data}")
        
        if not data or 'prompt' not in data:
            logger.error("Missing prompt parameter in request")
            status_code = 400
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='missing_parameter').inc()
            return jsonify({"error": "Missing prompt parameter"}), status_code
        
        if not api_key:
            logger.error("Cannot call OpenAI API: OPENAI_API_KEY is not set")
            status_code = 500
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='api_key_missing').inc()
            return jsonify({"error": "OpenAI API key is not configured"}), status_code
            
        # Call OpenAI API
        logger.debug("Calling OpenAI API...")
        try:
            model = "gpt-3.5-turbo"
            with track_llm_request(metrics_dict, 'openai', model) as tracker:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                        {"role": "user", "content": data['prompt']}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # Estimate token usage
                prompt_tokens = len(data['prompt']) / 4  # Rough estimate
                response_tokens = len(response.choices[0].message.content) / 4  # Rough estimate
                tracker.record_tokens(input_tokens=prompt_tokens, output_tokens=response_tokens)
                
            logger.debug(f"OpenAI response type: {type(response)}")
            logger.debug(f"OpenAI response: {response}")
            
            if not response.choices or len(response.choices) == 0:
                logger.error("No choices in OpenAI response")
                status_code = 500
                metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='empty_response').inc()
                return jsonify({"error": "No response from OpenAI"}), status_code
                
            # Return the raw response from OpenAI
            content = response.choices[0].message.content
            logger.debug(f"Response content: {content}")
            
            # Try to parse the content as JSON to validate it
            try:
                parsed_json = json.loads(content)
                # If it's valid JSON, return it as an object
                return jsonify(parsed_json)
            except json.JSONDecodeError as e:
                logger.warning(f"OpenAI response is not valid JSON: {e}")
                metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='invalid_json').inc()
                # If it's not valid JSON, wrap it in a response object
                return jsonify({"response": content, "warning": "Response was not valid JSON"})
            
        except Exception as e:
            error_stack = traceback.format_exc()
            logger.error(f"OpenAI API error: {str(e)}")
            logger.error(f"Stack trace: {error_stack}")
            status_code = 500
            metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='openai_api_error').inc()
            return jsonify({"error": f"OpenAI API error: {str(e)}"}), status_code
            
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Error in predict route: {str(e)}")
        logger.error(f"Stack trace: {error_stack}")
        status_code = 500
        metrics_dict['api_errors_total'].labels(method='POST', endpoint='/predict', error_type='server_error').inc()
        return jsonify({"error": str(e)}), status_code
    finally:
        # Record request metrics
        duration = time.time() - start_time
        metrics_dict['api_request_duration'].labels(method='POST', endpoint='/predict').observe(duration)
        metrics_dict['api_requests_total'].labels(method='POST', endpoint='/predict', status=status_code).inc()

# ----------------------------------------------
# Health Check Endpoint
# ----------------------------------------------

@app.route('/health', methods=['GET'])
def health_endpoint():
    start_time = time.time()
    status_code = 200
    try:
        if not api_key:
            status_code = 500
            metrics_dict['api_errors_total'].labels(method='GET', endpoint='/health', error_type='api_key_missing').inc()
            return jsonify({"status": "unhealthy", "error": "OPENAI_API_KEY environment variable not set"}), status_code
            
        # Simple test completion to check API connectivity
        with track_llm_request(metrics_dict, 'openai', 'gpt-3.5-turbo') as tracker:
            client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            # Estimate token usage (minimal for health check)
            tracker.record_tokens(input_tokens=1, output_tokens=1)
            
        return jsonify({"status": "healthy", "model": "gpt-3.5-turbo", "openai_status": "connected"}), status_code
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"OpenAI connection error: {str(e)}")
        logger.error(f"Stack trace: {error_stack}")
        status_code = 500
        metrics_dict['api_errors_total'].labels(method='GET', endpoint='/health', error_type='openai_connection_error').inc()
        return jsonify({"status": "unhealthy", "error": f"OpenAI connection error: {str(e)}", "openai_status": "disconnected"}), status_code
    finally:
        # Record request metrics
        duration = time.time() - start_time
        metrics_dict['api_request_duration'].labels(method='GET', endpoint='/health').observe(duration)
        metrics_dict['api_requests_total'].labels(method='GET', endpoint='/health', status=status_code).inc()

# ----------------------------------------------
# Metrics Endpoint (automatically added by PrometheusMetrics)
# ----------------------------------------------

# ----------------------------------------------
# Main Execution
# ----------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
