#!/usr/bin/env python3

from aws_cdk import core
from aws_es_recommended_cw_alarms.aws_es_recommended_cw_alarms_stack import (
    AwsEsRecommendedCwAlarmsStack,
)
import os
import sys

app = core.App()

CFN_STACK_NAME, ES_DOMAIN_ARN, AWS_PROFILE, CW_TRIGGER_SNS_ARN_LIST, ENABLE_ES_API_OUTPUT, ES_API_OUTPUT_SNS_ARN = (
    sys.argv[1],
    sys.argv[2],
    sys.argv[3],
    None if sys.argv[4] == 'None' else sys.argv[4].split(","),
    sys.argv[5] == "True",
    None if sys.argv[6] == 'None' else sys.argv[6],
)

AwsEsRecommendedCwAlarmsStack(
    app,
    CFN_STACK_NAME,
    ES_DOMAIN_ARN,
    AWS_PROFILE,
    CW_TRIGGER_SNS_ARN_LIST,
    ENABLE_ES_API_OUTPUT,
    ES_API_OUTPUT_SNS_ARN,
    env={"account": ES_DOMAIN_ARN.split(":")[4], "region": ES_DOMAIN_ARN.split(":")[3]},
)

app.synth()
