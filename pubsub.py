# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from awscrt import mqtt
import sys
import threading
import time
from uuid import uuid4
import json
import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
from base64 import b64encode
import cv2
import face_recognition
import boto3
import pickle

picam2 = Picamera2()
picam2.start()
time.sleep(2)

GPIO.setmode(GPIO.BOARD)

# Set the servo pin (e.g., pin 12)
servo_pin = 12

# Set up the servo pin as an output
GPIO.setup(servo_pin, GPIO.OUT)

# Set the PWM frequency (50 Hz is common for servos)
pwm_frequency = 50
pwm = GPIO.PWM(servo_pin, pwm_frequency)
pwm.start(0)
known_face_encodings, known_face_names = [],[]

# Function to convert degrees to duty cycle
def degrees_to_duty_cycle(degrees):
    min_duty_cycle = 2  # 0 degrees
    max_duty_cycle = 12  # 180 degrees
    return min_duty_cycle + (degrees / 180) * (max_duty_cycle - min_duty_cycle)

def s3(str,serialized_data):
    s3_client = boto3.client('s3')
    bucket_name = 'distance-iot-ultrasonic-shravya'
    key = 'encodings'
    # Read the file contents from the S3 bucket
    if str == "download":
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        file_contents = response['Body'].read()
        data = pickle.loads(file_contents)
        return (data["encodings"], data["names"])
    else:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=serialized_data)

# This sample uses the Message Broker for AWS IoT to send and receive messages
# through an MQTT connection. On startup, the device connects to the server,
# subscribes to a topic, and begins publishing messages to that topic.
# The device should receive those same messages back from the message broker,
# since it is subscribed to that same topic.

# Parse arguments
import utils.command_line_utils as command_line_utils
cmdUtils = command_line_utils.CommandLineUtils("PubSub - Send and recieve messages through an MQTT connection.")
cmdUtils.add_common_mqtt_commands()
cmdUtils.add_common_topic_message_commands()
cmdUtils.add_common_proxy_commands()
cmdUtils.add_common_logging_commands()
cmdUtils.register_command("key", "<path>", "Path to your key in PEM format.", True, str)
cmdUtils.register_command("cert", "<path>", "Path to your client certificate in PEM format.", True, str)
cmdUtils.register_command("port", "<int>", "Connection port. AWS IoT supports 443 and 8883 (optional, default=auto).", type=int)
cmdUtils.register_command("client_id", "<str>", "Client ID to use for MQTT connection (optional, default='test-*').", default="test-" + str(uuid4()))
cmdUtils.register_command("count", "<int>", "The number of messages to send (optional, default='10').", default=10, type=int)
cmdUtils.register_command("is_ci", "<str>", "If present the sample will run in CI mode (optional, default='None')")
# Needs to be called so the command utils parse the commands
cmdUtils.get_args()

received_count = 0
received_all_event = threading.Event()
is_ci = cmdUtils.get_command("is_ci", None) != None

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count,pwm
    received_count += 1
    if received_count == cmdUtils.get_command("count"):
        received_all_event.set()

    payload_dict = json.loads(payload)
    global lock,not_allow
    if topic == "unlock":
    # Access the data in the dictionary
        unlock_status = payload_dict["unlock"]
        if unlock_status == "yes":
            # Do something when unlock is "yes"
            print("Unlock: Yes")
            pwm.ChangeDutyCycle(degrees_to_duty_cycle(90))
            time.sleep(5)

            # Move servo to 180 degrees
            pwm.ChangeDutyCycle(degrees_to_duty_cycle(0))
            time.sleep(1)
            print("locked")
            lock = False
        else:
            not_allow = True

    elif topic == "remember":
        global known_face_encodings,known_face_names, face_encodings
        known_face_encodings.append(face_encodings[0])
        known_face_names.append("user"+str(len(known_face_names)))
        data = {"encodings": known_face_encodings, "names": known_face_names}
        s3("upload",pickle.dumps(data))

        pwm.ChangeDutyCycle(degrees_to_duty_cycle(90))
        time.sleep(5)

            # Move servo to 180 degrees
        pwm.ChangeDutyCycle(degrees_to_duty_cycle(0))
        time.sleep(1)
        print("locked")
        lock = False


if __name__ == '__main__':
    mqtt_connection = cmdUtils.build_mqtt_connection(on_connection_interrupted, on_connection_resumed)

    if is_ci == False:
        print("Connecting to {} with client ID '{}'...".format(
            cmdUtils.get_command(cmdUtils.m_cmd_endpoint), cmdUtils.get_command("client_id")))
    else:
        print("Connecting to endpoint with client ID")
    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    message_count = cmdUtils.get_command("count")
    message_topic = cmdUtils.get_command(cmdUtils.m_cmd_topic)
    message_string = "My Sensor"

    # Subscribe
    print("Subscribing to topic.")
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic="unlock",
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)
    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))
    
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic="remember",
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    known_face_encodings,known_face_names= s3("download", None)
    face_encodings = []
    
    # Publish message to server desired number of times.
    # This step is skipped if message is blank.
    # This step loops forever if count was set to 0.
    if message_string:
        if message_count == 0:
            print ("Sending messages until program killed")
        else:
            print ("Sending {} message(s)".format(message_count))

        publish_count = 1
        while (publish_count <= message_count) or (message_count == 0):

            image = picam2.capture_array("main")
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            lock = True 
            not_allow = False
            face_locations = face_recognition.face_locations(rgb_image,model="hog")
            if  len(face_locations) >0 :
                face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                jpeg_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
                _, jpeg_bytes = cv2.imencode('.jpg', rgb_image, jpeg_params)
                b64 = b64encode(jpeg_bytes)

                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # See if the face is a match for any known faces
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

                    name = "Unknown"

                    if True in matches:
                        first_match_index = matches.index(True)
                        name = known_face_names[first_match_index]

                #"image":b64.decode("utf-8"),
                message = {"image":b64.decode("utf-8"),"host":"shravya","name":name}
                message["permitted"] = "yes" if name != "Unknown" else "no"
                print("Publishing message to topic '{}': {}".format(message_topic, message["host"]))
                message_json = json.dumps(message)
                mqtt_connection.publish(
                    topic=message_topic,
                    payload=message_json,
                    qos=mqtt.QoS.AT_LEAST_ONCE)
                print("waiting ")
                while lock:
                    time.sleep(1)
                    if not_allow:
                        break
                print("locked and continuing ")
                lock = True
                time.sleep(2)
                publish_count += 1

    # Wait for all messages to be received.
    # This waits forever if count was set to 0.
    if message_count != 0 and not received_all_event.is_set():
        print("Waiting for all messages to be received...")

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
