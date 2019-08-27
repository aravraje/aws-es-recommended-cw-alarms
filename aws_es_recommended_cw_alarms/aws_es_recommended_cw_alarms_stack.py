from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_lambda_event_sources as _lambda_event_source,
    aws_iam as iam,
    aws_sns as sns,
)
from aws_es_cw_alarms import AwsEsRecommendedCwAlarms
import boto3

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, domain_arn: str, aws_cli_profile: str = None, sns_topic_arn_list: list = [], **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        AwsEsRecommendedCwAlarms(self, 'aws-es-cw-alarms', domain_arn, aws_cli_profile, sns_topic_arn_list)

        # Getting the ES domain endpoint via boto3
        profile_name = aws_cli_profile if aws_cli_profile else "default"
        session = boto3.Session(profile_name=profile_name)
        es_client = session.client("es")
        response = es_client.describe_elasticsearch_domain(DomainName=domain_arn.split("/")[1])[
            "DomainStatus"
        ]

        domain_endpoint = response["Endpoint"]

        # Creating a Lambda function to invoke ES _cat APIs corresponding to the triggered CW Alarm
        self._lambda_func = _lambda.Function(
            self,
            'CWAlarmHandler',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('lambda'),
            handler='lambda_function.lambda_handler',
            timeout=core.Duration.minutes(1),
            environment={
                "DOMAIN_ENDPOINT": domain_endpoint,
                "DOMAIN_ARN": domain_arn,
            } 
        )

        # A Custom IAM Policy statement to grant _cat API access to the Lambda function
        self._es_policy_statement = iam.PolicyStatement(
            actions=['es:ESHttpHead', 'es:ESHttpGet'],
            effect=iam.Effect.ALLOW,
            resources=[domain_arn + '/*']
        )

        self._lambda_func.add_to_role_policy(
            self._es_policy_statement
        )
        
        # Attaching a SNS topic provided by the user as the trigger for the Lambda function
        # If more than one SNS topic is provided, we will attach just the first SNS topic as the trigger
        self._sns_topic = sns.Topic.from_topic_arn(self, sns_topic_arn_list[0].split(":")[-1], sns_topic_arn_list[0])

        # Adding an SNS trigger to the Lambda function
        self._lambda_func.add_event_source(
            _lambda_event_source.SnsEventSource(self._sns_topic)
        )

        # Adding SNS Publish permission since the Lambda function is configured to post 
        # the output of _cat APIs to the same SNS topic that triggers the function
        self._sns_publish_policy_statement = iam.PolicyStatement(
            actions=['SNS:Publish'],
            effect=iam.Effect.ALLOW,
            resources=[self._sns_topic.topic_arn]
        )

        self._lambda_func.add_to_role_policy(
            self._sns_publish_policy_statement
        )