import boto3
import requests
from requests_aws4auth import AWS4Auth
import os
import json
from time import sleep

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
        "_nodes/hot_threads", # instead of doing hot_threads from all nodes, do only from overloaded nodes
        "_cat/thread_pool?v",
        "_nodes/stats/os?pretty", 
    ],
    "JVMMemoryPressure": [
        "_nodes/stats/jvm?pretty",
    ],

    # for master, add cat pending tasks API and master API
}

def lambda_handler(event, context):
    sns_message = json.loads(event["Records"][0]["Sns"]["Message"])
    cw_metric = sns_message["Trigger"]["MetricName"]

    host = 'https://' + os.environ['DOMAIN_ENDPOINT'] + '/'
    region = os.environ['DOMAIN_ARN'].split(":")[3]
    service = os.environ['DOMAIN_ARN'].split(":")[2]
    awsauth = AWS4Auth(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'], region, service, session_token=os.environ['AWS_SESSION_TOKEN'])
    headers = {"Content-Type": "application/json"}

    if 'SNS_TOPIC_ARN' in os.environ:
        sns_topic_arn = os.environ['SNS_TOPIC_ARN']

    send_to_es(host, cw_metric, METRIC_TO_API_MAPPING[cw_metric], awsauth, headers, sns_topic_arn=None)

def send_to_es(host, cw_metric, apis, awsauth, headers, sns_topic_arn):
    api_output = {'apis': []}
    for api in apis:
        out = {}
        out['domain_endpoint'] = os.environ['DOMAIN_ENDPOINT']
        out['metric_name'] = cw_metric
        out['api'] = api
        try:
            r = requests.get(host + api, auth=awsauth, headers=headers, timeout=30)
            r.raise_for_status()
            out['response'] = r.text

        except Exception as e:
            # print(f"An unknown error occurred while invoking the API - {api}: {e}")
            out['exception'] = e

        finally:
            print(out)

        api_output['apis'].append(out)

    if api_output['apis'] and sns_topic_arn:
        sns = boto3.client('sns')
        max_retries = 3
        num_retries = 0
        backoff = 1 #In Seconds
        sns_response = None
        
        while num_retries <= max_retries:
            sns_response = sns.publish(
                TopicArn=sns_topic_arn,
                Message=api_output,
            )

            if 'MessageId' in sns_response:
                break
            
            num_retries += 1
            sleep(num_retries * backoff)
        
        if num_retries > max_retries:
            print(f"An unknown error occurred while publishing to the SNS topic: {sns_response}")