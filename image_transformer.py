import json
from PIL import Image, ImageDraw
import base64
import random
import io
import uuid
import requests
import boto3

def send_message_to_slack(slack_information, message_payload):
  webhook_url = slack_information["webhook"]
  headers = {"Content-Type": "application/json",}

  response = requests.post(
                    webhook_url,
                    headers=headers,
                    json=message_payload,
                    )

def get_slack_information(file_path):
  with open(file_path) as json_file:
    data = json.load(json_file)
    return data

def prepare_slack_mesage(s3_file_name, bucket):
  return 'You have a new transformed image "{file_name}" in S3 bucket "{bucket}"'.format(file_name=s3_file_name, bucket=bucket)

def write_encoded_string_to_image_file(file_path, encoded_string):
  with open(file_path, "wb") as f:
    f.write(base64.b64decode(encoded_string))

def upload_image_to_s3(file_path, bucket, format):
  s3_client = boto3.client('s3')
  key = "{id}.{format}".format(id=uuid.uuid4(), format=format)

  s3_client.upload_file(file_path, bucket, key)

  return key

def convert_image_to_base64_string(image):
  buffered = io.BytesIO()
  image.save(buffered, format="JPEG")
  image_string = base64.b64encode(buffered.getvalue()).decode('ascii')

  return image_string

def shuffle_image_color(image):
  # split the color bands of the image
  r, g, b = image.split()

  # create a list of the colors
  rgb = [r, g, b]

  # shuffle the order of red, green and blue
  random.shuffle(rgb)

  # merge the image back together
  image = Image.merge("RGB", rgb)

  return image

def resize_image(image):
  image.thumbnail([512,512], Image.ANTIALIAS)

def transform_image(file_path):
  # read the image from disk
  image = Image.open(file_path)
  
  # merge the color with random order
  image = shuffle_image_color(image)

  # resize image to uniform format
  resize_image(image)

  # encode the picture to a base64 response
  image_string = convert_image_to_base64_string(image)

  # save image to disk
  image.save(file_path)

  image.close()

  return image_string

def lambda_handler(event, context):

  # initialize parameters
  file_path = "/tmp/image.jpg"
  s3_bucket = "lambda-transformed-images"
  lambda_runtime_root = "/var/task/"
  slack_information_file_path = lambda_runtime_root + "slack.json"
  http_status_code = 200

  write_encoded_string_to_image_file(file_path, event["body"])    

  # shuffle, resize and encode the picture to a base64 response
  image_string = transform_image(file_path)

  try:
    # upload image to s3
    s3_file_name = upload_image_to_s3(file_path, s3_bucket, "jpg")

    slack_information = get_slack_information(slack_information_file_path)

    message = prepare_slack_mesage(s3_file_name, s3_bucket)
    message_payload = {"user": slack_information["user"], "message": message}
    send_message_to_slack(slack_information, message_payload)

  except Exception as e:
    http_status_code = 500
    print(e)

  finally:

    # Return the data to API Gateway in base64.
    # API Gateway will handle the conversion back to binary.
    # Set content-type header as image/jpeg.
    return {
      "isBase64Encoded": True,
      "statusCode": http_status_code,
      "headers": { "content-type": "image/jpeg"},
      "body":  image_string
    }
