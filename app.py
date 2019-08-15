#!/usr/bin/env python3

from aws_cdk import core

from aws_es_recommended_cw_alarms.aws_es_recommended_cw_alarms_stack import AwsEsRecommendedCwAlarmsStack


app = core.App()
AwsEsRecommendedCwAlarmsStack(app, "aws-es-recommended-cw-alarms")

app.synth()
