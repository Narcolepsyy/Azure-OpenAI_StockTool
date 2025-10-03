"""AWS services package."""
from .s3_service import S3Service, get_s3_service
from .dynamodb_service import DynamoDBService, get_dynamodb_service
from .sqs_service import SQSService, get_sqs_service
from .cloudwatch_service import CloudWatchService, get_cloudwatch_service

__all__ = [
    'S3Service',
    'get_s3_service',
    'DynamoDBService',
    'get_dynamodb_service',
    'SQSService',
    'get_sqs_service',
    'CloudWatchService',
    'get_cloudwatch_service',
]
