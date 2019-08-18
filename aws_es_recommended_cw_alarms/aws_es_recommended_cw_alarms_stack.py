from aws_cdk import (
    core, 
    aws_cloudwatch as cloudwatch, 
    aws_lambda as _lambda
)
import boto3
import json
import sys

"""
Use this only for ES >= 5.x.
Only log things that are not there in the K2.
Get Data node volume size and number of node (master + data) from user.
"""

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, domain_arn: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Getting the domain name from the ARN
        domain_name = domain_arn.split("/")[1]

        # Getting the domain details via boto3
        session = boto3.Session(profile_name='araviraj')
        es_client = session.client('es')
        response = es_client.describe_elasticsearch_domain(
            DomainName=domain_name
        )['DomainStatus']

        if float(response['ElasticsearchVersion']) < 5.1:
            print('Domains with ES version < 5.1 is not supported.')
            sys.exit()

        node_count = response['ElasticsearchClusterConfig']['InstanceCount']

        if response['ElasticsearchClusterConfig']['DedicatedMasterEnabled']:
            node_count = node_count + response['ElasticsearchClusterConfig']['DedicatedMasterCount']

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric
        self._RedClusterAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-RedClusterAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterStatus.red",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=2500,
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
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
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(5),
            evaluation_periods=3,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the MasterCPUUtilization metric
        self._MasterCPUUtilizationAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-MasterCPUUtilizationAlarm",
            metric=cloudwatch.Metric(
                metric_name="MasterCPUUtilization",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=50,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(15),
            evaluation_periods=3,
            statistic="avg",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the MasterJVMMemoryPressure metric
        self._MasterJVMMemoryPressureAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-MasterJVMMemoryPressureAlarm",
            metric=cloudwatch.Metric(
                metric_name="MasterJVMMemoryPressure",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(15),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the KMSKeyError metric
        self._KMSKeyErrorAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-KMSKeyErrorAlarm",
            metric=cloudwatch.Metric(
                metric_name="KMSKeyError",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )

        # Setting a Cloudwatch Alarm on the KMSKeyInaccessible metric
        self._KMSKeyInaccessibleAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-KMSKeyInaccessibleAlarm",
            metric=cloudwatch.Metric(
                metric_name="KMSKeyInaccessible",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name, "ClientId": core.Stack.of(self).account},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.MISSING,
        )