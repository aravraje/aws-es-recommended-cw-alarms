import boto3
import requests
from requests_aws4auth import AWS4Auth
import os
import json
from time import sleep

# Mapping ES _cluster, _cat, _nodes APIs to the corresponding CW Metric
METRIC_TO_API_MAPPING = {
    "ClusterStatus.red": [
        "_cluster/health?pretty",
        "_cluster/allocation/explain?format=json",
        "_cat/indices?v&health=red&s=index",
    ],
    "ClusterStatus.yellow": [
        "_cluster/health?pretty",
        "_cluster/allocation/explain?format=json",
        "_cat/indices?v&health=yellow&s=index",
    ],
    "FreeStorageSpace": [
        "_cat/allocation?v&s=disk.percent:desc",
        "_cat/indices?v&s=store.size:desc",
    ],
    "ClusterIndexWritesBlocked": [
        "_cat/allocation?v&s=disk.percent:desc",
        "_nodes/stats/jvm?pretty",
    ],
    "CPUUtilization": [
        "_cat/nodes?v&s=cpu:desc",
        "_nodes/hot_threads",
    ],
    "JVMMemoryPressure": [
        "_nodes/stats/jvm?pretty",
        "_cat/fielddata?v",
    ],
    "MasterCPUUtilization": [
        "_cat/master?v",
        "_cat/pending_tasks?v",
    ],
}


def lambda_handler(event, context):

    # Return if "es_api_output_sns_arn" is the same as the one configured with "cw_trigger_sns_arn_list" in the "configure" script
    if "IS_CW_ALARM" in event["Records"][0]["Sns"]["MessageAttributes"]:
        return
    
    sns_message = json.loads(event["Records"][0]["Sns"]["Message"])
    cw_metric = sns_message["Trigger"]["MetricName"]

    host = "https://" + os.environ["DOMAIN_ENDPOINT"] + "/"
    region = os.environ["DOMAIN_ARN"].split(":")[3]
    service = os.environ["DOMAIN_ARN"].split(":")[2]

    # Building a SigV4 request
    awsauth = AWS4Auth(
        os.environ["AWS_ACCESS_KEY_ID"],
        os.environ["AWS_SECRET_ACCESS_KEY"],
        region,
        service,
        session_token=os.environ["AWS_SESSION_TOKEN"],
    )
    headers = {"Content-Type": "application/json"}

    # Sending the API calls to ES
    if "SNS_TOPIC_ARN" in os.environ:
        send_to_es(
            host,
            cw_metric,
            METRIC_TO_API_MAPPING[cw_metric],
            awsauth,
            headers,
            os.environ["SNS_TOPIC_ARN"]
        )
    else:
        send_to_es(
            host, 
            cw_metric, 
            METRIC_TO_API_MAPPING[cw_metric], 
            awsauth, 
            headers
        )


def send_to_es(host, cw_metric, apis, awsauth, headers, sns_topic_arn=None):
    api_output = {
        "apis": []
    }

    # Invoking the ES _cluster/_cat/_nodes APIs one after the other and adding their output to a list
    for api in apis:
        num_retries, max_retries = 0, 3
        es_backoff = 5 # In Seconds
        out = {}
        out["domain_endpoint"] = os.environ["DOMAIN_ENDPOINT"]
        out["metric_name"] = cw_metric
        out["api"] = api
        while num_retries < max_retries:
            try:
                r = requests.get(host + api, auth=awsauth, headers=headers, timeout=30)
                r.raise_for_status()
                out["response"] = r.text
                out.pop("exception", None)
                break

            except Exception as e:
                out["exception"] = e
                num_retries += 1
                sleep(num_retries * es_backoff)

        api_output["apis"].append(out)

    print(f"ES API output: \n{api_output}")

    # If "es_api_output_sns_arn" is configured via the "configure" script, sending the ES API outputs to SNS
    if sns_topic_arn:
        sns = boto3.client("sns")
        num_retries, max_retries = 0, 3
        sns_backoff = 1  # In Seconds
        sns_response = None

        while num_retries < max_retries:
            sns_response = sns.publish(
                TopicArn=sns_topic_arn,
                Message=json.dumps(api_output),
                MessageAttributes={
                    "IS_CW_ALARM": {"DataType": "String", "StringValue": "False"}
                },
            )

            if "MessageId" in sns_response:
                break

            num_retries += 1
            sleep(num_retries * sns_backoff)

        if num_retries == max_retries:
            print(f"An unknown error occurred while publishing the ES API output to the SNS topic: \n{sns_response}")
