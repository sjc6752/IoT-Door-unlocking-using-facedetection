AWS IMPLEMENTATION

1. Connect your device to AWS IoT core and download the connection kit
2. Follow the same steps as in tutorial 2 by cloning GitHub repo https://github.com/aws/aws-iot-device-sdk-python-v2  and install it using "python3 setup.py install"
3. Attatch the policy.json file to the exisiting certificate.
4. Create 4 lambda functions with names : face_detection_function, face_detection_remember , face_detection_yes, face_detection_no and copy the code from .py files with respective names in the repo to the created functions.
5. Create a rule and configure the sql statement as "SELECT * FROM 'sdk/test/python'". Select Lambda as an action. Select face_detection_function.
6. Create a Rest API with Regional end point. Create 3 resources with names : `yes`, `no` , `remember`. Create `GET` method for all three resources. Integrate respective Lambda functions created in step 4. Deploy the API and note down the URL for each resource.
7. Replace the yes, no , remember URLs in "notify_host" function in lambda face_detection_function with the above noted URLs appropriately.
8. Create an AWS Dynamo Table to save the records.
9. Create an AWS s3 Bucket to save encodings and update it when a new face is added. Create encodings key and Upload encodings file in above repo.
10. Replace the code in ./aws-iot-device-sdk-python-v2/samples/pubsub.py with the code in above repo's pubsub.py.

NOTE : 
1. Create a ./aws folder and a credentials file for authenticating to AWS. Please reach out to me for ACCESS KEY and SECRET KEY. 
2. You can also change email ids in face_detection_function for receiving notifications to unlock the door.

EXECUTION :

1. Run ./start.sh file to start running the project.
2. Camera module starts face detection and recognition until program is killed.