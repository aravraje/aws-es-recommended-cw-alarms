#!/usr/bin/env python3

from aws_cdk import core
from aws_es_recommended_cw_alarms.aws_es_recommended_cw_alarms_stack import AwsEsRecommendedCwAlarmsStack
import os

app = core.App()

AwsEsRecommendedCwAlarmsStack(app, "aws-es-recommended-cw-alarms", os.environ["ES_DOMAIN_ARN"].split("/")[1], env={
    "account": os.environ["CDK_DEFAULT_ACCOUNT"] or os.environ["ES_DOMAIN_ARN"].split(":")[4],
    "region": os.environ["CDK_DEFAULT_REGION"] or os.environ["ES_DOMAIN_ARN"].split(":")[3],
})

app.synth()