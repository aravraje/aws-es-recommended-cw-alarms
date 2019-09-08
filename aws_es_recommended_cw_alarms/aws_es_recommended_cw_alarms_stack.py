from aws_cdk import (
    core,
)
from aws_es_cw_alarms import AwsEsRecommendedCwAlarms
import boto3


class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        domain_arn: str,
        aws_cli_profile: str = None,
        cw_trigger_sns_arn_list: list = [],
        enable_es_api_output: bool = False,
        es_api_output_sns_arn: str = None,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        AwsEsRecommendedCwAlarms(
            self, "aws-es-cw-alarms", domain_arn, aws_cli_profile, cw_trigger_sns_arn_list, enable_es_api_output, es_api_output_sns_arn
        )
