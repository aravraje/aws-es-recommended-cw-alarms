from aws_cdk import (
    core,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_lambda as _lambda,
    aws_lambda_event_sources as _lambda_event_source,
    aws_iam as iam,
    aws_sns as sns,
    aws_ec2 as ec2,
)
import boto3


class AwsEsRecommendedCwAlarms(core.Construct):

    _account = _domain_name = _domain_endpoint = None
    _volume_size = _node_count = None
    _is_dedicated_master_enabled = _is_encryption_at_rest_enabled = _is_vpc_domain = False
    _vpc = _security_group = None
    _subnets = _azs = _sns_topic_list = []
    _instance_store_volume_size = {
        "m3.medium.elasticsearch": 4,
        "m3.large.elasticsearch": 32,
        "m3.xlarge.elasticsearch": 80,
        "m3.2xlarge.elasticsearch": 160,
        "r3.large.elasticsearch": 32,
        "r3.xlarge.elasticsearch": 80,
        "r3.2xlarge.elasticsearch": 160,
        "r3.4xlarge.elasticsearch": 320,
        "r3.8xlarge.elasticsearch": 640,
        "i3.large.elasticsearch": 475,
        "i3.xlarge.elasticsearch": 950,
        "i3.2xlarge.elasticsearch": 1900,
        "i3.4xlarge.elasticsearch": 3800,
        "i3.8xlarge.elasticsearch": 7600,
        "i3.16xlarge.elasticsearch": 15200,
        "i2.xlarge.elasticsearch": 800,
        "i2.2xlarge.elasticsearch": 1600,
    }

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        domain_arn: str,
        aws_cli_profile: str = None,
        cw_trigger_sns_arn_list: list = [],
        enable_es_api_output: bool = False,
        es_api_output_sns_arn: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Configuring certain aspects of the stack based on the ES domain details
        self.configure(domain_arn, aws_cli_profile, cw_trigger_sns_arn_list)

        # Setting a Cloudwatch Alarm on the ClusterStatus.red metric
        self.create_cw_alarm_with_action(
            "ClusterStatus.red",
            1,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            1,
            1,
            "max",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the ClusterStatus.yellow metric
        self.create_cw_alarm_with_action(
            "ClusterStatus.yellow",
            1,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            1,
            1,
            "max",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the FreeStorageSpace metric. The threshold is 25% of the current volume size (in MB) of a data node.
        self.create_cw_alarm_with_action(
            "FreeStorageSpace",
            self._volume_size * 0.25 * 1000,
            cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            1,
            1,
            "min",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the ClusterIndexWritesBlocked metric
        self.create_cw_alarm_with_action(
            "ClusterIndexWritesBlocked",
            1,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            5,
            1,
            "max",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the Nodes metric
        self.create_cw_alarm_with_action(
            "Nodes",
            self._node_count,
            cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            1440,
            1,
            "min",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the AutomatedSnapshotFailure metric
        self.create_cw_alarm_with_action(
            "AutomatedSnapshotFailure",
            1,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            1,
            1,
            "max",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the CPUUtilization metric
        self.create_cw_alarm_with_action(
            "CPUUtilization",
            80,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            15,
            3,
            "avg",
            self._sns_topic_list,
        )

        # self.create_cw_alarm_with_action(
        #     "CPUUtilization", 80, cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD, 1, 1, "max", self._sns_topic_list
        # )

        # Setting a Cloudwatch Alarm on the JVMMemoryPressure metric
        self.create_cw_alarm_with_action(
            "JVMMemoryPressure",
            80,
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            5,
            3,
            "max",
            self._sns_topic_list,
        )

        # Setting a Cloudwatch Alarm on the MasterCPUUtilization & MasterJVMMemoryPressure metrics
        # only if Dedicated Master is enabled
        if self._is_dedicated_master_enabled:
            self.create_cw_alarm_with_action(
                "MasterCPUUtilization",
                50,
                cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                15,
                3,
                "avg",
                self._sns_topic_list,
            )

            self.create_cw_alarm_with_action(
                "MasterJVMMemoryPressure",
                80,
                cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                15,
                1,
                "max",
                self._sns_topic_list,
            )

        # Setting a Cloudwatch Alarm on the KMSKeyError & KMSKeyInaccessible metrics
        # only if Encryption at Rest config is enabled
        if self._is_encryption_at_rest_enabled:
            self.create_cw_alarm_with_action(
                "KMSKeyError",
                1,
                cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                1,
                1,
                "max",
                self._sns_topic_list,
            )

            self.create_cw_alarm_with_action(
                "KMSKeyInaccessible",
                1,
                cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                1,
                1,
                "max",
                self._sns_topic_list,
            )
        
        if enable_es_api_output:
            # Creating a Lambda function to invoke ES _cat APIs corresponding to the triggered CW Alarm
            if self._is_vpc_domain:
                self._lambda_vpc = ec2.Vpc.from_lookup(
                    self,
                    self._vpc,
                    vpc_id=self._vpc
                )

                self._lambda_subnets = [
                    ec2.Subnet.from_subnet_attributes(
                        self,
                        self._subnets[i],
                        subnet_id=self._subnets[i],
                        availability_zone=self._azs[i]
                    )
                    for i in range(0, len(self._subnets))
                ]

                self._lambda_security_group = ec2.SecurityGroup.from_security_group_id(
                    self,
                    self._security_group,
                    security_group_id=self._security_group
                )

                self._lambda_security_group.add_ingress_rule(
                    ec2.Peer().prefix_list(self._security_group),
                    ec2.Port.tcp(443),
                    description="Ingress rule that allows the aws_es_cw_alarms Lambda to talk to VPC based ES domain"
                )

                self._lambda_func = _lambda.Function(
                    self,
                    "CWAlarmHandler",
                    runtime=_lambda.Runtime.PYTHON_3_7,
                    code=_lambda.Code.asset("lambda"),
                    handler="lambda_function.lambda_handler",
                    timeout=core.Duration.minutes(1),
                    environment={
                        "DOMAIN_ENDPOINT": self._domain_endpoint, 
                        "DOMAIN_ARN": domain_arn
                    },
                    vpc=self._lambda_vpc,
                    vpc_subnets=ec2.SubnetSelection(subnets=self._lambda_subnets),
                    security_group=self._lambda_security_group
                )
            else:
                self._lambda_func = _lambda.Function(
                    self,
                    "CWAlarmHandler",
                    runtime=_lambda.Runtime.PYTHON_3_7,
                    code=_lambda.Code.asset("lambda"),
                    handler="lambda_function.lambda_handler",
                    timeout=core.Duration.minutes(1),
                    environment={
                        "DOMAIN_ENDPOINT": self._domain_endpoint, 
                        "DOMAIN_ARN": domain_arn
                    },
                )

            # A Custom IAM Policy statement to grant _cat API access to the Lambda function
            self._es_policy_statement = iam.PolicyStatement(
                actions=["es:ESHttpHead", "es:ESHttpGet"],
                effect=iam.Effect.ALLOW,
                resources=[domain_arn + "/*"],
            )

            self._lambda_func.add_to_role_policy(self._es_policy_statement)

            # Attaching a SNS topic provided by the user as the trigger for the Lambda function
            # If more than one SNS topic is provided, we will attach just the first SNS topic as the trigger
            self._lambda_func.add_event_source(
                _lambda_event_source.SnsEventSource(self._sns_topic_list[0])
            )

            if es_api_output_sns_arn:
                self._lambda_func.add_environment("SNS_TOPIC_ARN", es_api_output_sns_arn)

                # Adding SNS Publish permission since the Lambda function is configured to post
                # the output of _cat APIs to the same SNS topic that triggers the function
                self._sns_publish_policy_statement = iam.PolicyStatement(
                    actions=["SNS:Publish"],
                    effect=iam.Effect.ALLOW,
                    resources=[es_api_output_sns_arn],
                )

                self._lambda_func.add_to_role_policy(self._sns_publish_policy_statement)

    def configure(self, domain_arn, aws_cli_profile, cw_trigger_sns_arn_list):
        self._domain_name = domain_arn.split("/")[1]
        self._account = domain_arn.split(":")[4]

        # Initializing the SNS topic(s) if provided by the user
        if cw_trigger_sns_arn_list:
            for sns_topic_arn in cw_trigger_sns_arn_list:
                self._sns_topic_list.append(
                    sns.Topic.from_topic_arn(
                        self, sns_topic_arn.split(":")[-1], sns_topic_arn
                    )
                )

        # Getting the domain details via boto3
        profile_name = aws_cli_profile if aws_cli_profile else "default"
        session = boto3.Session(profile_name=profile_name)
        es_client = session.client("es")
        response = es_client.describe_elasticsearch_domain(
            DomainName=self._domain_name
        )["DomainStatus"]

        if "VPCOptions" in response:
            self._is_vpc_domain = True
            self._domain_endpoint = response["Endpoints"]["vpc"]
            self._vpc = response["VPCOptions"]["VPCId"]
            self._subnets = response["VPCOptions"]["SubnetIds"]
            self._azs = response["VPCOptions"]["AvailabilityZones"]
            self._security_group = response["VPCOptions"]["SecurityGroupIds"][0]
        else:
            self._domain_endpoint = response["Endpoint"]

        # Deciding volume size based on EBS or Instance store
        if response["EBSOptions"]["EBSEnabled"]:
            self._volume_size = response["EBSOptions"]["VolumeSize"]
        else:
            self._volume_size = self._instance_store_volume_size[
                response["ElasticsearchClusterConfig"]["InstanceType"]
            ]

        self._is_dedicated_master_enabled = response["ElasticsearchClusterConfig"][
            "DedicatedMasterEnabled"
        ]

        # Node count is usually the num. of Data nodes unless Dedicated Master is enabled;
        # Otherwise, it's num. of Data nodes + Dedicated Master nodes
        self._node_count = response["ElasticsearchClusterConfig"]["InstanceCount"]
        if self._is_dedicated_master_enabled:
            self._node_count += response["ElasticsearchClusterConfig"][
                "DedicatedMasterCount"
            ]

        self._is_encryption_at_rest_enabled = response["EncryptionAtRestOptions"][
            "Enabled"
        ]

    def create_cw_alarm_with_action(
        self,
        metric_name,
        threshold,
        comparison_operator,
        period,
        evaluation_periods,
        statistic,
        sns_topic_list=[],
    ) -> None:
        # Creating a CW Alarm for the provided metric
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

        # If SNS topic list is provided by the user, setting the Alarm action to the topic(s)
        if sns_topic_list:
            self._cw_alarm.add_alarm_action(
                *list(map(cloudwatch_actions.SnsAction, sns_topic_list))
            )
