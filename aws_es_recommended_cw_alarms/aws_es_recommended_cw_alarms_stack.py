from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_iam as iam,
)
from aws_es_cw_alarms import AwsEsRecommendedCwAlarms

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, domain_arn: str, aws_cli_profile: str = None, sns_topic_arn_list: list = [], **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        AwsEsRecommendedCwAlarms(self, 'aws-es-cw-alarms', domain_arn, aws_cli_profile, sns_topic_arn_list)

        self._es_policy_statement = iam.PolicyStatement(
            actions=['es:ESHttpHead', 'es:ESHttpGet'],
            effect=iam.Effect.ALLOW,
            resources=[domain_arn + '/*']
        )

        self._lambda_func = _lambda.Function(
            self,
            'CWAlarmHandler',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('lambda'),
            handler='lambda_function.lambda_handler',
            timeout=core.Duration.minutes(1),
            environment={ #DOMAIN_ENDPOINT is without protocol; Need to dynamically get this in the future
                "DOMAIN_ENDPOINT": "search-aravirajtestdomain-ayp6ly7mdmohvcbekpaywpmr2y.us-east-1.es.amazonaws.com",
                "DOMAIN_ARN": domain_arn,
            } 
        )

        self._lambda_func.add_to_role_policy(
            self._es_policy_statement
        )
        