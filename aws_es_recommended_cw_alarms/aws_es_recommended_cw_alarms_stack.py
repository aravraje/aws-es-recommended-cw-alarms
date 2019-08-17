from aws_cdk import (
    core, 
    aws_cloudwatch as cloudwatch, 
    aws_lambda as _lambda
)

'''Use this only for ES >= 5.x'''

'''Only log things that are not there in the K2'''

class AwsEsRecommendedCwAlarmsStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, domain_name: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric

        '''
        cat/indices (to display the red indices) - display primary/replica shard count
        cluster/allocation/explain
        '''

        self._RedClusterAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-RedClusterAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterStatus.red",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        '''
        cat/indices (to display the red indices) - display primary/replica shard count
        cluster/allocation/explain
        '''
        # Setting a Cloudwatch Alarm on the ClusterStatus.yellow metric
        self._YellowClusterAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-YellowClusterAlarm",
            metric=cloudwatch.Metric(
                metric_name="ClusterStatus.yellow",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name},
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="max",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Ask customer to input it
        self._FreeStorageSpaceAlarm = cloudwatch.Alarm(
            self,
            domain_name + "-FreeStorageSpaceAlarm",
            metric=cloudwatch.Metric(
                metric_name="FreeStorageSpace",
                namespace="AWS/ES",
                dimensions={"DomainName": domain_name},
            ),
            threshold=20480,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            period=core.Duration.minutes(1),
            evaluation_periods=1,
            statistic="min",
            treat_missing_data=cloudwatch.TreatMissingData.IGNORE,
        )