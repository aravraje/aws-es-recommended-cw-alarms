#!/usr/bin/env python3

from aws_cdk import core
from aws_es_recommended_cw_alarms.aws_es_recommended_cw_alarms_stack import AwsEsRecommendedCwAlarmsStack
import os

app = core.App()

AwsEsRecommendedCwAlarmsStack(
    app, 
    "aws-es-recommended-cw-alarms", 
    os.environ["ES_DOMAIN_ARN"], 
    'araviraj', 
    ['arn:aws:sns:us-east-1:854759189838:testTopic', 'arn:aws:sns:us-east-1:854759189838:newTopic'], 
    env={
        "account": os.environ["ES_DOMAIN_ARN"].split(":")[4] or os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["ES_DOMAIN_ARN"].split(":")[3] or os.environ["CDK_DEFAULT_REGION"],
    }
)

app.synth()