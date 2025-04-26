from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge
import time

def setup_metrics(app, service_name):
    """
    Set up Prometheus metrics for a Flask application
    
    Args:
        app: Flask application
        service_name: Name of the service (used as a label)
    
    Returns:
        PrometheusMetrics object
    """
    metrics = PrometheusMetrics(app, group_by='endpoint')
    
    # Add default metrics
    metrics.info('app_info', f'{service_name} service info', version='1.0.0')
    
    # Create custom metrics
    api_requests_total = Counter(
        'api_requests_total', 
        f'Total number of requests to {service_name} API',
        ['method', 'endpoint', 'status']
    )
    
    api_request_duration = Histogram(
        'api_request_duration_seconds', 
        f'Duration of {service_name} API requests',
        ['method', 'endpoint']
    )
    
    api_errors_total = Counter(
        'api_errors_total', 
        f'Total number of errors in {service_name} API',
        ['method', 'endpoint', 'error_type']
    )
    
    # For LLM services
    llm_requests_total = Counter(
        'llm_requests_total', 
        'Total number of requests to the LLM API',
        ['service', 'model']
    )
    
    llm_request_duration = Histogram(
        'llm_request_duration_seconds', 
        'Duration of LLM API requests',
        ['service', 'model']
    )
    
    llm_tokens_total = Counter(
        'llm_tokens_total', 
        'Total number of tokens processed',
        ['service', 'model', 'type']  # type can be 'input' or 'output'
    )
    
    # System metrics
    system_memory_usage = Gauge(
        'system_memory_usage_bytes', 
        'Current memory usage of the application',
        ['service']
    )
    
    # Return all metrics for use in the application
    return {
        'metrics': metrics,
        'api_requests_total': api_requests_total,
        'api_request_duration': api_request_duration,
        'api_errors_total': api_errors_total,
        'llm_requests_total': llm_requests_total,
        'llm_request_duration': llm_request_duration,
        'llm_tokens_total': llm_tokens_total,
        'system_memory_usage': system_memory_usage
    }

def track_llm_request(metrics_dict, service, model, start_time=None):
    """Helper function to track LLM request metrics"""
    if start_time is None:
        start_time = time.time()
        
    # Return a context manager for timing
    class LLMRequestTracker:
        def __init__(self, metrics_dict, service, model, start_time):
            self.metrics_dict = metrics_dict
            self.service = service
            self.model = model
            self.start_time = start_time
            
        def __enter__(self):
            # Increment the counter when entering the context
            self.metrics_dict['llm_requests_total'].labels(service=self.service, model=self.model).inc()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            # Record the duration when exiting
            duration = time.time() - self.start_time
            self.metrics_dict['llm_request_duration'].labels(service=self.service, model=self.model).observe(duration)
            
        def record_tokens(self, input_tokens=0, output_tokens=0):
            # Record token counts
            if input_tokens:
                self.metrics_dict['llm_tokens_total'].labels(service=self.service, model=self.model, type='input').inc(input_tokens)
            if output_tokens:
                self.metrics_dict['llm_tokens_total'].labels(service=self.service, model=self.model, type='output').inc(output_tokens)
    
    return LLMRequestTracker(metrics_dict, service, model, start_time) 