import json
import numpy as np
import cv2
from base64 import b64decode
import boto3
import time
import base64
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import pickle
import tempfile
import os
import datetime


s3_client = boto3.client('s3')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('project_IOT')
ses_client = boto3.client('ses')
iot_data_client = boto3.client('iot-data')


# {"image":"xyz","host": "shravys",'permitted':"yes","name":"shravya"}
def store_in_table(event: dict) -> None:
    item = {
        'ID': str(datetime.datetime.now()),
        'Name': event["name"],
        'encoded_image': event["image"],
        "host":event["host"],
        "is_permitted": event["permitted"]
    }

    response = table.put_item(Item=item)

def notify_host(event: dict) -> None:

    JPEG_r = base64.b64decode(event["image"])
    na_r = cv2.imdecode(np.frombuffer(JPEG_r,dtype=np.uint8), cv2.IMREAD_COLOR)
    filename = "/tmp/my_image.png"
    cv2.imwrite(filename, na_r)

    RECIPIENT = 'shravyachillamcherla@gmail.com'
    SENDER=  "rakshith.gannarapu@gmail.com"
    SUBJECT = 'Smart Unlock: Authorization required'
    CHARSET = 'UTF-8'

    with open(filename, 'rb') as f:
        image_data = f.read()
    
    # image_base64 = base64.b64encode(image_data).decode('utf-8')

    msg = MIMEMultipart('related')
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER
    msg['To'] = RECIPIENT
    
    html_part = MIMEText(
        """<!DOCTYPE html>
                    <html>
                    <head>
                        <title>Yes or No Option</title>
                    </head>
                    <body>
                        <h1>Someone is at your door. Would you like to allow?</h1>
                        <a href="https://z5jnrhj7k5.execute-api.us-east-2.amazonaws.com/live/yes"><button>Yes</button></a>
                        <a href="https://z5jnrhj7k5.execute-api.us-east-2.amazonaws.com/live/no"><button>No</button></a>
                        <a href="https://z5jnrhj7k5.execute-api.us-east-2.amazonaws.com/live/remember"><button>Remember</button></a>
                        <p><img src="cid:image1"></p>
                    </body>
                    </html>
                """,'html'
        )
        
    msg.attach(html_part)
    
    image = MIMEImage(image_data,name="image.jpg")
    image.add_header('Content-ID','<image1>')
    msg.attach(image)


    try:
        response = ses_client.send_raw_email(
            Source = msg['From'],
            Destinations = [msg["To"]],
            RawMessage = {'Data': msg.as_string()}
            )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:", response['MessageId'])

def lambda_handler(event, context):
    input = event
    
    if input["permitted"] == "yes":
        
        event["permitted"] = True
        store_in_table(event)
        
        payload = {
        "unlock":"yes"
        }
    
        # Publish the message to the MQTT topic
        response = iot_data_client.publish(
            topic="unlock",
            qos=1,
            payload=json.dumps(payload)
        )
        
    else:
        event["permitted"] = False
        store_in_table(event)
        notify_host(event)
    

