import requests
from requests_aws4auth import AWS4Auth
import os
import json
import re

METRIC_TO_CAT_API_MAPPING = {
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
        "_nodes/hot_threads",
        "_cat/thread_pool?v",
        "_nodes/stats/os?pretty", 
    ],
    "JVMMemoryPressure": [
        "_nodes/stats/jvm?pretty",
    ],

    # for master, add cat pending tasks API and master API
}

def lambda_handler(event, context):
    sns_message = event['Records'][0]["Sns"]["Message"]
    cw_metric = sns_message["Trigger"]["MetricName"]

    host = 'https://' + os.environ['DOMAIN_ENDPOINT'] + '/'
    region = os.environ['DOMAIN_ARN'].split(":")[3]
    service = os.environ['DOMAIN_ARN'].split(":")[2]
    awsauth = AWS4Auth(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'], region, service, session_token=os.environ['AWS_SESSION_TOKEN'])
    headers = {"Content-Type": "application/json"}

    send_to_es(host, cw_metric, METRIC_TO_CAT_API_MAPPING[cw_metric], awsauth, headers)

def send_to_es(host, cw_metric, apis, awsauth, headers):
    for api in apis:
        try:
            r = requests.get(host + api, auth=awsauth, headers=headers)
            if r.status_code == 200:
                print("===================================")
                print(f"Domain Endpoint: {os.environ['DOMAIN_ENDPOINT']}\nMetric Name: {cw_metric}\nAPI: {api}")
                print("===================================")
                print(r.text)
        
        except Exception as e:
            print(e)