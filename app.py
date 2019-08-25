#!/usr/bin/env python3

from aws_cdk import core
from aws_es_recommended_cw_alarms.aws_es_recommended_cw_alarms_stack import AwsEsRecommendedCwAlarmsStack
import os
import sys

app = core.App()

CFN_STACK_NAME, ES_DOMAIN_ARN, AWS_PROFILE, SNS_TOPIC_LIST_ARN = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")

AwsEsRecommendedCwAlarmsStack(
    app, 
    CFN_STACK_NAME,
    ES_DOMAIN_ARN, 
    AWS_PROFILE, 
    SNS_TOPIC_LIST_ARN, 
    env={
        "account": ES_DOMAIN_ARN.split(":")[4],
        "region": ES_DOMAIN_ARN.split(":")[3],
    }
)

app.synth()