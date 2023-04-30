import boto3
import json

def lambda_handler(event, context):
    iot_data_client = boto3.client('iot-data')

    # Prepare the message payload
    payload = {
        "unlock":"yes"
    }

    # Publish the message to the MQTT topic
    response = iot_data_client.publish(
        topic="unlock",
        qos=1,
        payload=json.dumps(payload)
    )
    
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Access Granted')
    }
