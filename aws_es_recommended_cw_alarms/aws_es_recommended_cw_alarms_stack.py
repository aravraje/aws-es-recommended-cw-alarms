from aws_cdk import (
    core, 
    aws_cloudwatch as cloudwatch, 
    aws_lambda as _lambda
)
import boto3


class AwsEsRecommendedCwAlarmsStack(core.Stack):

    _domain_name = _account = _volume_size = _node_count = None

    _is_dedicated_master_enabled = _is_encryption_at_rest_enabled = False

    instance_store_volume_size = {
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

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric
        self._RedClusterAlarm = self.create_cw_alarm(
            "ClusterStatus.red", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max"
        )

        # Setting a Cloudwatch Alarm on the ClusterStatus.yellow metric
        self._YellowClusterAlarm = self.create_cw_alarm(
            "ClusterStatus.yellow", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max"
        )

        # Setting a Cloudwatch Alarm on the FreeStorageSpace metric. The threshold is 25% of the current volume size (in MB) of a data node.
        self._FreeStorageSpaceAlarm = self.create_cw_alarm(
            "FreeStorageSpace", self._volume_size * 0.25 * 1000, cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "min"
        )
        
        # Setting a Cloudwatch Alarm on the ClusterIndexWritesBlocked metric
        self._ClusterBlockAlarm = self.create_cw_alarm(
            "ClusterIndexWritesBlocked", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 5, 1, "max"
        )

        # Setting a Cloudwatch Alarm on the Nodes metric
        self._NodesAlarm = self.create_cw_alarm(
            "Nodes", self._node_count, cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD, 1440, 1, "min"
        )

        # Setting a Cloudwatch Alarm on the AutomatedSnapshotFailure metric
        self._AutomatedSnapshotFailureAlarm = self.create_cw_alarm(
            "AutomatedSnapshotFailure", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max"
        )

        # Setting a Cloudwatch Alarm on the CPUUtilization metric
        self._CPUUtilizationAlarm = self.create_cw_alarm(
            "CPUUtilization", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 3, "avg"
        )

        # Setting a Cloudwatch Alarm on the JVMMemoryPressure metric
        self._JVMMemoryPressureAlarm = self.create_cw_alarm(
            "JVMMemoryPressure", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 5, 3, "max"
        )

        # Setting a Cloudwatch Alarm on the MasterCPUUtilization & MasterJVMMemoryPressure metrics
        # only if Dedicated Master is enabled
        if self._is_dedicated_master_enabled:
            self._MasterCPUUtilizationAlarm = self.create_cw_alarm(
                "MasterCPUUtilization", 50, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 3, "avg"
            )

            self._MasterJVMMemoryPressureAlarm = self.create_cw_alarm(
                "MasterJVMMemoryPressure", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 15, 1, "max"
            )

        # Setting a Cloudwatch Alarm on the KMSKeyError & KMSKeyInaccessible metrics
        # only if Encryption at Rest config is enabled
        if self._is_encryption_at_rest_enabled:
            self._KMSKeyErrorAlarm = self.create_cw_alarm(
                "KMSKeyError", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max"
            )

            self._KMSKeyInaccessibleAlarm = self.create_cw_alarm(
                "KMSKeyInaccessible", 1, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max"
            )


    def configure(self, domain_arn, aws_cli_profile):
        self._domain_name = domain_arn.split("/")[1]
        self._account = domain_arn.split(":")[4]

        # Getting the domain details via boto3
        profile_name = "default" if aws_cli_profile is None else aws_cli_profile

        session = boto3.Session(profile_name=profile_name)
        es_client = session.client("es")
        response = es_client.describe_elasticsearch_domain(DomainName=self._domain_name)[
            "DomainStatus"
        ]

        if response["EBSOptions"]["EBSEnabled"]:
            self._volume_size = response["EBSOptions"]["VolumeSize"]
        else:
            self._volume_size = instance_store_volume_size[
                response["ElasticsearchClusterConfig"]["InstanceType"]
            ]

        self._is_dedicated_master_enabled = response["ElasticsearchClusterConfig"][
            "DedicatedMasterEnabled"
        ]
        self._node_count = response["ElasticsearchClusterConfig"]["InstanceCount"]
        if self._is_dedicated_master_enabled:
            self._node_count += response["ElasticsearchClusterConfig"]["DedicatedMasterCount"]

        self._is_encryption_at_rest_enabled = response["EncryptionAtRestOptions"]["Enabled"]


    def create_cw_alarm(self, metric_name, threshold, comparison_operator, period, evaluation_periods, statistic) -> cloudwatch.IAlarm:
        return cloudwatch.Alarm(
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