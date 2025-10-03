"""AWS CloudWatch service for metrics and logging."""
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

logger = logging.getLogger(__name__)


class CloudWatchService:
    """Service for CloudWatch metrics and logs."""
    
    def __init__(self, namespace: str = "StockTool", endpoint_url: Optional[str] = None):
        """
        Initialize CloudWatch service.
        
        Args:
            namespace: CloudWatch namespace for metrics
            endpoint_url: Optional endpoint URL (for LocalStack)
        """
        self.namespace = namespace
        
        # Configure with timeouts and retries
        config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=5,
            read_timeout=10
        )
        
        # Use endpoint_url if provided (LocalStack)
        client_kwargs = {
            'config': config,
            'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }
        
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
            client_kwargs['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            client_kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        
        self.cloudwatch_client = boto3.client('cloudwatch', **client_kwargs)
        self.logs_client = boto3.client('logs', **client_kwargs)
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'None',
        dimensions: Optional[List[Dict[str, str]]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Put a metric data point.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit (Seconds, Milliseconds, Count, Percent, etc.)
            dimensions: Optional dimensions list
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            True if successful
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': timestamp or datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = dimensions
            
            self.cloudwatch_client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Put metric {metric_name}={value} {unit}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to put metric: {e}")
            return False
    
    def put_metrics_batch(
        self,
        metrics: List[Dict[str, Any]],
        batch_size: int = 20
    ) -> bool:
        """
        Put multiple metrics in batches.
        
        Args:
            metrics: List of metric dicts with keys: name, value, unit, dimensions, timestamp
            batch_size: Batch size (max 20 for CloudWatch)
            
        Returns:
            True if all batches successful
        """
        success = True
        
        for i in range(0, len(metrics), batch_size):
            batch = metrics[i:i+batch_size]
            metric_data = []
            
            for metric in batch:
                data = {
                    'MetricName': metric['name'],
                    'Value': metric['value'],
                    'Unit': metric.get('unit', 'None'),
                    'Timestamp': metric.get('timestamp', datetime.utcnow())
                }
                
                if 'dimensions' in metric:
                    data['Dimensions'] = metric['dimensions']
                
                metric_data.append(data)
            
            try:
                self.cloudwatch_client.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=metric_data
                )
                logger.debug(f"Put batch of {len(metric_data)} metrics")
            except (ClientError, BotoCoreError) as e:
                logger.error(f"Failed to put metric batch: {e}")
                success = False
        
        return success
    
    def track_api_latency(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int = 200
    ):
        """
        Track API endpoint latency.
        
        Args:
            endpoint: API endpoint name
            latency_ms: Latency in milliseconds
            status_code: HTTP status code
        """
        self.put_metric(
            metric_name='APILatency',
            value=latency_ms,
            unit='Milliseconds',
            dimensions=[
                {'Name': 'Endpoint', 'Value': endpoint},
                {'Name': 'StatusCode', 'Value': str(status_code)}
            ]
        )
    
    def track_tool_execution(
        self,
        tool_name: str,
        execution_time_ms: float,
        success: bool = True
    ):
        """
        Track tool execution time.
        
        Args:
            tool_name: Name of the tool
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
        """
        self.put_metric(
            metric_name='ToolExecutionTime',
            value=execution_time_ms,
            unit='Milliseconds',
            dimensions=[
                {'Name': 'Tool', 'Value': tool_name},
                {'Name': 'Status', 'Value': 'Success' if success else 'Failure'}
            ]
        )
    
    def track_cache_hit_rate(
        self,
        cache_name: str,
        hit: bool
    ):
        """
        Track cache hit rate.
        
        Args:
            cache_name: Name of the cache
            hit: Whether it was a cache hit
        """
        self.put_metric(
            metric_name='CacheHitRate',
            value=100.0 if hit else 0.0,
            unit='Percent',
            dimensions=[
                {'Name': 'Cache', 'Value': cache_name}
            ]
        )
    
    def track_model_usage(
        self,
        model_name: str,
        tokens_used: int,
        response_time_ms: float
    ):
        """
        Track LLM model usage.
        
        Args:
            model_name: Name of the model
            tokens_used: Number of tokens used
            response_time_ms: Response time in milliseconds
        """
        metrics = [
            {
                'name': 'ModelTokens',
                'value': tokens_used,
                'unit': 'Count',
                'dimensions': [{'Name': 'Model', 'Value': model_name}]
            },
            {
                'name': 'ModelLatency',
                'value': response_time_ms,
                'unit': 'Milliseconds',
                'dimensions': [{'Name': 'Model', 'Value': model_name}]
            }
        ]
        self.put_metrics_batch(metrics)
    
    def create_log_group(self, log_group_name: str) -> bool:
        """
        Create a log group.
        
        Args:
            log_group_name: Name of the log group
            
        Returns:
            True if created or already exists
        """
        try:
            self.logs_client.create_log_group(logGroupName=log_group_name)
            logger.info(f"Created log group: {log_group_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                logger.debug(f"Log group already exists: {log_group_name}")
                return True
            logger.error(f"Failed to create log group: {e}")
            return False
    
    def put_log_event(
        self,
        log_group_name: str,
        log_stream_name: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Put a log event.
        
        Args:
            log_group_name: Name of the log group
            log_stream_name: Name of the log stream
            message: Log message
            timestamp: Optional timestamp
            
        Returns:
            True if successful
        """
        try:
            # Ensure log stream exists
            try:
                self.logs_client.create_log_stream(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                    raise
            
            # Put log event
            self.logs_client.put_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                logEvents=[{
                    'timestamp': int((timestamp or datetime.utcnow()).timestamp() * 1000),
                    'message': message
                }]
            )
            
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to put log event: {e}")
            return False
    
    def query_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        period: int = 300,
        stat: str = 'Average',
        dimensions: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query metric statistics.
        
        Args:
            metric_name: Name of the metric
            start_time: Start time for query
            end_time: Optional end time (defaults to now)
            period: Period in seconds
            stat: Statistic (Average, Sum, Maximum, Minimum, SampleCount)
            dimensions: Optional dimensions filter
            
        Returns:
            List of metric data points
        """
        try:
            params = {
                'Namespace': self.namespace,
                'MetricName': metric_name,
                'StartTime': start_time,
                'EndTime': end_time or datetime.utcnow(),
                'Period': period,
                'Statistics': [stat]
            }
            
            if dimensions:
                params['Dimensions'] = dimensions
            
            response = self.cloudwatch_client.get_metric_statistics(**params)
            
            datapoints = response.get('Datapoints', [])
            # Sort by timestamp
            datapoints.sort(key=lambda x: x['Timestamp'])
            
            logger.info(f"Retrieved {len(datapoints)} datapoints for {metric_name}")
            return datapoints
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to query metrics: {e}")
            return []
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get performance summary for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict with performance metrics
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        summary = {}
        
        # API Latency
        latency_data = self.query_metrics(
            'APILatency',
            start_time,
            end_time,
            period=300,
            stat='Average'
        )
        if latency_data:
            summary['avg_api_latency_ms'] = sum(d['Average'] for d in latency_data) / len(latency_data)
        
        # Tool Execution Time
        tool_data = self.query_metrics(
            'ToolExecutionTime',
            start_time,
            end_time,
            period=300,
            stat='Average'
        )
        if tool_data:
            summary['avg_tool_time_ms'] = sum(d['Average'] for d in tool_data) / len(tool_data)
        
        # Cache Hit Rate
        cache_data = self.query_metrics(
            'CacheHitRate',
            start_time,
            end_time,
            period=300,
            stat='Average'
        )
        if cache_data:
            summary['avg_cache_hit_rate'] = sum(d['Average'] for d in cache_data) / len(cache_data)
        
        return summary


# Singleton instance
_cloudwatch_service: Optional[CloudWatchService] = None


def get_cloudwatch_service() -> CloudWatchService:
    """Get or create CloudWatch service singleton."""
    global _cloudwatch_service
    
    if _cloudwatch_service is None:
        namespace = os.getenv('CLOUDWATCH_NAMESPACE', 'StockTool')
        endpoint_url = os.getenv('AWS_ENDPOINT_URL') if os.getenv('USE_LOCALSTACK', 'false').lower() == 'true' else None
        _cloudwatch_service = CloudWatchService(namespace, endpoint_url)
    
    return _cloudwatch_service
