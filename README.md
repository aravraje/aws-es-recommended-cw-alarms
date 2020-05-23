
# AWS ES Recommended CW Alarms

An AWS CDK (Python) based solution to implement the Recommended CloudWatch Alarms for AWS Elasticsearch (https://amzn.to/2NltKqy) in any AWS account. The solution also includes a Lambda function that is pre-coded to invoke ES _cat, _cluster, _node APIs (on a best-effort basis) corresponding to the triggered CloudWatch Alarm.


## How to deploy?

#### Prerequisites

* Python >= 3.7
  * https://www.python.org/downloads/
  * Installing on EC2 Linux - https://docs.aws.amazon.com/cli/latest/userguide/install-linux-python.html

* Node.js >= 10.3.0 (required for the AWS CDK Toolkit)
  * https://nodejs.org/en/download
  * Installing on EC2 Linux - https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-up-node-on-ec2-instance.html#setting-up-node-on-ec2-instance-procedure

* AWS CLI with at least the "default" profile configured
  * https://docs.aws.amazon.com/cli/latest/userguide/install-cliv1.html
  * https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration

* AWS CDK
  * https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_install

* Git CLI
  * https://git-scm.com/downloads

#### Steps

1. Clone the project

```
$ git clone https://github.com/aravraje/aws-es-recommended-cw-alarms.git
```

2. Navigate to the project folder and create a Python virtualenv (assuming that there is a python3 (or python for Windows) executable in your path with access to the venv package)

```
$ python3 -m venv .env
```

3. Activate the Python virtualenv

```
$ source .env/bin/activate
```

  - If you are on a Windows platform, you can activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

4. Once the virtualenv is activated, install the required dependencies

```
$ pip install -r requirements.txt
```

5. Before deploying the solution, it needs to be configured with the AWS ES Domain ARN for which the Recommended CW Alarms should be created. To assist with this configuration, an helper script called "configure" is provided which has the below syntax:

```
$ ./configure -es_domain_arn <ES_DOMAIN_ARN> [-cfn_stack_name <CFN_STACK_NAME> -aws_profile <AWS_CLI_PROFILE> -cw_trigger_sns_arn_list <CW_TRIGGER_SNS_ARN_LIST> -enable_es_api_output <ENABLE_ES_API_OUTPUT> -es_api_output_sns_arn <ES_API_OUTPUT_SNS_ARN>]
```
  - NOTE: Please ensure that the AWS_CLI_PROFILE used here has DescribeElasticsearchDomain permission on the ES Domain.

> Using the helper script "configure", you can do other customizations to the solution (if required) apart from just configuring it with the AWS ES Domain ARN. For a complete list of customizations available to you, please invoke the below command:
> ```
> $ ./configure --help
> ```

6. After configuring the solution, you can deploy it using "cdk deploy" CDK CLI command

> NOTE: If this is your first time deploying a CDK app in the given AWS Account and Region, you must bootstrap your AWS environment for CDK by invoking "cdk bootstrap" CDK CLI command before running the "cdk deploy" command.

```
$ cdk deploy [--profile aws_cli_profile]
```
  - NOTE: The aws_cli_profile used here should be the same as the one that was used when configuring the solution via "configure" helper script.
