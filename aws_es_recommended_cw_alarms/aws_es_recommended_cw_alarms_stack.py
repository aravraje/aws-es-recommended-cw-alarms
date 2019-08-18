from aws_cdk import (
    core, 
    aws_cloudwatch as cloudwatch, 
    aws_lambda as _lambda
)
import boto3
import json
import sys

"""
Use this only for AWS ES >= 5.1.
Only log things that are not there in the K2.
Get the domain ARN, CLI profile, Lambda action (optional) from the user
"""

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, domain_arn: str, aws_cli_profile: str=None, action_arn: str=None, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        domain_name = domain_arn.split("/")[1]
        account = domain_arn.split(":")[4]

        instance_store_volume_size = {
            'm3.medium.elasticsearch': 4,
            'm3.large.elasticsearch': 32,
            'm3.xlarge.elasticsearch': 80,
            'm3.2xlarge.elasticsearch': 160,
            'r3.large.elasticsearch': 32,
            'r3.xlarge.elasticsearch': 80,
            'r3.2xlarge.elasticsearch': 160,
            'r3.4xlarge.elasticsearch': 320,
            'r3.8xlarge.elasticsearch': 640,
            'i3.large.elasticsearch': 475,
            'i3.xlarge.elasticsearch': 950,
            'i3.2xlarge.elasticsearch': 1900,
            'i3.4xlarge.elasticsearch': 3800,
            'i3.8xlarge.elasticsearch': 7600,
            'i3.16xlarge.elasticsearch': 15200,
            'i2.xlarge.elasticsearch': 800,
            'i2.2xlarge.elasticsearch': 1600,
        }

        # Getting the domain details via boto3
        profile_name = 'default' if aws_cli_profile is None else aws_cli_profile

        session = boto3.Session(profile_name=profile_name)
        es_client = session.client('es')
        response = es_client.describe_elasticsearch_domain(
            DomainName=domain_name
        )['DomainStatus']

        '''
        if float(response['ElasticsearchVersion']) < 5.1:
            print('Domains with ES version < 5.1 is not supported.')
            sys.exit()
        '''

        volume_size = None
        if response['EBSOptions']['EBSEnabled']:
            volume_size = response['EBSOptions']['VolumeSize']
        else:
            volume_size = instance_store_volume_size[response['ElasticsearchClusterConfig']['InstanceType']]

        is_dedicated_master_enabled = response['ElasticsearchClusterConfig']['DedicatedMasterEnabled']
        node_count = response['ElasticsearchClusterConfig']['InstanceCount']
        if is_dedicated_master_enabled:
            node_count = node_count + response['ElasticsearchClusterConfig']['DedicatedMasterCount']

        is_encryption_at_rest_enabled = response['EncryptionAtRestOptions']['Enabled']

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric
        self._RedClusterAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-RedClusterAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterStatus.red",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Setting a Cloudwatch Alarm on the ClusterStatus.yellow metric
        self._YellowClusterAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-YellowClusterAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterStatus.yellow",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Setting a Cloudwatch Alarm on the FreeStorageSpace metric (the value for 'threshold' is user provided)
        self._FreeStorageSpaceAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-FreeStorageSpaceAlarm",
            metric=cloudwatch.Metric(
                metric_name="FreeStorageSpace",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=volume_size * 0.25 * 1000, # 25% of the current volume size (in MB) of a data node
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="min",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the ClusterIndexWritesBlocked metric
        self._ClusterBlockAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-ClusterBlockAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterIndexWritesBlocked",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(5),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the Nodes metric
        self._NodesAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-NodesAlarm",
            metric=cloudwatch.Metric(
                metric_name="Nodes",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=node_count,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            period=core.Duration.days(1),
            evaluation_periods=1,
            statistic="min",
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
        )

        # Setting a Cloudwatch Alarm on the AutomatedSnapshotFailure metric
        self._AutomatedSnapshotFailureAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-AutomatedSnapshotFailureAlarm",
            metric=cloudwatch.Metric(
                metric_name="AutomatedSnapshotFailure",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the CPUUtilization metric
        self._CPUUtilizationAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-CPUUtilizationAlarm",
            metric=cloudwatch.Metric(
                metric_name="CPUUtilization",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(15),
            evaluation_periods=3,
            statistic="avg",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the JVMMemoryPressure metric
        self._JVMMemoryPressureAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-JVMMemoryPressureAlarm",
            metric=cloudwatch.Metric(
                metric_name="JVMMemoryPressure",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": account},
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(5),
            evaluation_periods=3,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the MasterCPUUtilization & MasterJVMMemoryPressure metrics 
        # only if Dedicated Master is enabled
        if is_dedicated_master_enabled:            
            self._MasterCPUUtilizationAlarm = cloudwatch.Alarm(
                self,
                domain_name + "-MasterCPUUtilizationAlarm",
                metric=cloudwatch.Metric(
                    metric_name="MasterCPUUtilization",
                    namespace="AWS/ES",
                    dimensions={"DomainName": domain_name, "ClientId": account},
                ),
                threshold=50,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                period=core.Duration.minutes(15),
                evaluation_periods=3,
                statistic="avg",
                treat_missing_data=cloudwatch.TreatMissingData.MISSING,
            )

            self._MasterJVMMemoryPressureAlarm = cloudwatch.Alarm(
                self,
                domain_name + "-MasterJVMMemoryPressureAlarm",
                metric=cloudwatch.Metric(
                    metric_name="MasterJVMMemoryPressure",
                    namespace="AWS/ES",
                    dimensions={"DomainName": domain_name, "ClientId": account},
                ),
                threshold=80,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                period=core.Duration.minutes(15),
                evaluation_periods=1,
                statistic="max",
                treat_missing_data=cloudwatch.TreatMissingData.MISSING,
            )

        # Setting a Cloudwatch Alarm on the KMSKeyError & KMSKeyInaccessible metrics 
        # only if Encryption at Rest config is enabled
        if is_encryption_at_rest_enabled:
            self._KMSKeyErrorAlarm = cloudwatch.Alarm(
                self,
                domain_name + "-KMSKeyErrorAlarm",
                metric=cloudwatch.Metric(
                    metric_name="KMSKeyError",
                    namespace="AWS/ES",
                    dimensions={"DomainName": domain_name, "ClientId": account},
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                period=core.Duration.minutes(1),
                evaluation_periods=1,
                statistic="max",
                treat_missing_data=cloudwatch.TreatMissingData.MISSING,
            )

            self._KMSKeyInaccessibleAlarm = cloudwatch.Alarm(
                self,
                domain_name + "-KMSKeyInaccessibleAlarm",
                metric=cloudwatch.Metric(
                    metric_name="KMSKeyInaccessible",
                    namespace="AWS/ES",
                    dimensions={"DomainName": domain_name, "ClientId": account},
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                period=core.Duration.minutes(1),
                evaluation_periods=1,
                statistic="max",
                treat_missing_data=cloudwatch.TreatMissingData.MISSING,
            )
