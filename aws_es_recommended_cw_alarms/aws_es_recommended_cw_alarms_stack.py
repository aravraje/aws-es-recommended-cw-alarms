from aws_cdk import (
    core, 
    aws_cloudwatch as cloudwatch, 
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
)
import boto3


class AwsEsRecommendedCwAlarmsStack(core.Stack):

    _domain_name = _account = None

    _volume_size = _node_count = None

    _is_dedicated_master_enabled = _is_encryption_at_rest_enabled = False

    _sns_topic = None

    _instance_store_volume_size = {
        "m3.medium.elasticsearch": 4, "m3.large.elasticsearch": 32, "m3.xlarge.elasticsearch": 80,
        "m3.2xlarge.elasticsearch": 160, "r3.large.elasticsearch": 32, "r3.xlarge.elasticsearch": 80,
        "r3.2xlarge.elasticsearch": 160, "r3.4xlarge.elasticsearch": 320, "r3.8xlarge.elasticsearch": 640,
        "i3.large.elasticsearch": 475, "i3.xlarge.elasticsearch": 950, "i3.2xlarge.elasticsearch": 1900,
        "i3.4xlarge.elasticsearch": 3800, "i3.8xlarge.elasticsearch": 7600, "i3.16xlarge.elasticsearch": 15200,
        "i2.xlarge.elasticsearch": 800, "i2.2xlarge.elasticsearch": 1600,
    }

    def __init__(self, scope: core.Construct, id: str, domain_arn: str, aws_cli_profile: str = None, action_arn: str = None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.configure(domain_arn, aws_cli_profile)

        if action_arn:
            self._sns_topic = sns.Topic.from_topic_arn(self, 'AlarmActionTopic', action_arn)

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric
        self.create_cw_alarm_with_action(
            "ClusterStatus.red", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the ClusterStatus.yellow metric
        self.create_cw_alarm_with_action(
            "ClusterStatus.yellow", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the FreeStorageSpace metric. The threshold is 25% of the current volume size (in MB) of a data node.
        self.create_cw_alarm_with_action(
            "FreeStorageSpace", self._volume_size * 0.25 * 1000, cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "min", self._sns_topic
        )
        
        # Setting a Cloudwatch Alarm on the ClusterIndexWritesBlocked metric
        self.create_cw_alarm_with_action(
            "ClusterIndexWritesBlocked", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 5, 1, "max", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the Nodes metric
        self.create_cw_alarm_with_action(
            "Nodes", self._node_count, cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD, 1440, 1, "min", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the AutomatedSnapshotFailure metric
        self.create_cw_alarm_with_action(
            "AutomatedSnapshotFailure", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the CPUUtilization metric
        self.create_cw_alarm_with_action(
            "CPUUtilization", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 3, "avg", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the JVMMemoryPressure metric
        self.create_cw_alarm_with_action(
            "JVMMemoryPressure", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 5, 3, "max", self._sns_topic
        )

        # Setting a Cloudwatch Alarm on the MasterCPUUtilization & MasterJVMMemoryPressure metrics
        # only if Dedicated Master is enabled
        if self._is_dedicated_master_enabled:
            self.create_cw_alarm_with_action(
                "MasterCPUUtilization", 50, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 3, "avg", self._sns_topic
            )

            self.create_cw_alarm_with_action(
                "MasterJVMMemoryPressure", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 1, "max", self._sns_topic
            )

        # Setting a Cloudwatch Alarm on the KMSKeyError & KMSKeyInaccessible metrics
        # only if Encryption at Rest config is enabled
        if self._is_encryption_at_rest_enabled:
            self.create_cw_alarm_with_action(
                "KMSKeyError", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic
            )

            self.create_cw_alarm_with_action(
                "KMSKeyInaccessible", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic
            )


    def configure(self, domain_arn, aws_cli_profile):
        self._domain_name = domain_arn.split("/")[1]
        self._account = domain_arn.split(":")[4]

        # Getting the domain details via boto3
        profile_name = aws_cli_profile if aws_cli_profile else "default"

        session = boto3.Session(profile_name=profile_name)
        es_client = session.client("es")
        response = es_client.describe_elasticsearch_domain(DomainName=self._domain_name)[
            "DomainStatus"
        ]

        if response["EBSOptions"]["EBSEnabled"]:
            self._volume_size = response["EBSOptions"]["VolumeSize"]
        else:
            self._volume_size = self._instance_store_volume_size[
                response["ElasticsearchClusterConfig"]["InstanceType"]
            ]

        self._is_dedicated_master_enabled = response["ElasticsearchClusterConfig"][
            "DedicatedMasterEnabled"
        ]
        self._node_count = response["ElasticsearchClusterConfig"]["InstanceCount"]
        if self._is_dedicated_master_enabled:
            self._node_count += response["ElasticsearchClusterConfig"]["DedicatedMasterCount"]

        self._is_encryption_at_rest_enabled = response["EncryptionAtRestOptions"]["Enabled"]


    def create_cw_alarm_with_action(self, metric_name, threshold, comparison_operator, period, evaluation_periods, statistic, sns_topic=None) -> None:
        self._cw_alarm = cloudwatch.Alarm(
            self,
            self._domain_name + f"-{metric_name}Alarm",
            metric=cloudwatch.Metric(
                metric_name=metric_name,
                namespace="AWS/ES",
                dimensions={"DomainName": self._domain_name, "ClientId": self._account},
            ),
            threshold=threshold,
            comparison_operator=comparison_operator,
            period=core.Duration.minutes(period),
            evaluation_periods=evaluation_periods,
            statistic=statistic,
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        if sns_topic:
            self._cw_alarm.add_alarm_action(cloudwatch_actions.SnsAction(sns_topic))