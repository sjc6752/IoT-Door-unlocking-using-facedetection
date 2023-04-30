import json
import pickle
import tempfile
import os
import boto3

def lambda_handler(event, context):
    iot_data_client = boto3.client('iot-data')
    # Prepare the message payload
    payload = {
        "unlock":"yes"
    }
    
    response = iot_data_client.publish(
        topic="remember",
        qos=1,
        payload=json.dumps(payload)
    )
    
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Access granted and remembered')
    }
