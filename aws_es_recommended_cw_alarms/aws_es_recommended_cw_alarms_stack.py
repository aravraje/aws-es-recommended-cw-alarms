from aws_cdk import (
    core,
)
from aws_es_cw_alarms import AwsEsRecommendedCwAlarms

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, domain_arn: str, aws_cli_profile: str = None, sns_topic_arn_list: list = [], **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        AwsEsRecommendedCwAlarms(self, 'aws-es-cw-alarms', domain_arn, aws_cli_profile, sns_topic_arn_list)