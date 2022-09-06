# coding=utf-8
import base64
import boto3
import json
import urllib.parse
import os
import sys
import subprocess
from io import BytesIO
from decimal import Decimal

import botocore

subprocess.call('pip install Pillow -t /tmp/ --no-cache-dir'.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')
from PIL import Image

print('Loading function')

s3 = boto3.client('s3')
dynamodb = boto3.resource("dynamodb")

class DecimalEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      return str(obj)
    return json.JSONEncoder.default(self, obj)

def extractMetadata(event, context):
     # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)['Body'].read()

        # read the image
        image = Image.open(BytesIO(response))
        print(image.size)

        table = dynamodb.Table(os.getenv('DYNAMODB_TABLE', default=None))
        chave = key.split("uploads/")
        headImage = s3.head_object(Bucket=bucket, Key=key)
        table.put_item(
            Item={
                's3objectkey': chave[1],
                'size': headImage['ContentLength'],
                'Filename': key,
                'height': image.height,
                'width': image.width,
                'format': image.format,
                'mode': image.mode,
                'bucketname': bucket
            }
        )

        response = {
            'statusCode': 200,
            'body': 'item criado com sucesso',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
        }
  
        return response

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

def getMetadata(event, context):
    try:
        table = dynamodb.Table(os.getenv('DYNAMODB_TABLE', default=None))
        print('DADO DE ENTRADA')
        print(event)
        print(event['pathParameters'])
        path = event['pathParameters']
        print(path['s3objectkey'])

        bucket = os.getenv('BUCKET_NAME', default=None)
        key = 'uploads/' + path['s3objectkey']
        headImage = s3.head_object(Bucket=bucket, Key=key)

        # boto3 dynamodb getitem
        itemdynamo = table.get_item(
            Key={
                's3objectkey': path['s3objectkey'],
                'size': headImage['ContentLength']
            }
        )
        print(itemdynamo)
        image = itemdynamo['Item']
        print(image)
        info_image = {
                        'Filename': image['s3objectkey'],
                        'Image Size': image['size'],
                        'Image Height': image['height'],
                        'Image Width': image['width'],
                        'Image Format': image['format'],
                        'Image Mode': image['mode']
                    }

        response = {
            'statusCode': 200,
            'body': json.dumps(info_image, cls=DecimalEncoder),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
  
        return response

    except Exception as e:
        print(e)
        raise e

def getImage(event, context):
    try:
        path = event['pathParameters']
        key = 'uploads/' + path['s3objectkey']
        bucket = os.getenv('BUCKET_NAME', default=None)
        print(key)
        filepath = '/tmp/' + path['s3objectkey']
        response = s3.get_object(Bucket=bucket, Key=key)
        image_file_to_be_downloaded = response['Body'].read()
        return {
            'statusCode': 200,
            'headers': {
                           'Content-Type': 'application/jpg',
                           'Content-Disposition': 'attachment; filename={}'.format(path['s3objectkey'])
                       },
            'body': base64.b64encode(image_file_to_be_downloaded),
            'isBase64Encoded': True
        }

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise


def unique(list):
    # initialize a null list
    unique_list = {}

    # traverse for all elements
    for i in list:
        unique_list[i['format']] = sum(p['format'] == i['format'] for p in list)

    return unique_list

def getInfo(event, context):
    try:
        table = dynamodb.Table(os.getenv('DYNAMODB_TABLE',  default=None))
        bucket = os.getenv('BUCKET_NAME', default=None)
        response = table.scan()
        print(response)
        data = response['Items']
        listItens = response['Items']
        print(listItens)


        print('max')
        max_attr = max(listItens, key=lambda x: x['size'])
        print(max_attr)
        print('min')
        min_attr =min(listItens, key=lambda x: x['size'])
        print(min_attr)
        retornoDitcFormat = unique(listItens)
        print('formats')
        print(retornoDitcFormat.keys())

        print('quantidade')
        print(retornoDitcFormat)



        toJSON2 = json.dumps(retornoDitcFormat)
        print(toJSON2)

        infos = {
            'MAIOR IMAGEM': max_attr['s3objectkey'],
            'MENOR IMAGEM': min_attr['s3objectkey'],
            'FORMATOS E QUANTIDADES': toJSON2,

        }
        response = {
            'statusCode': 200,
            'body': json.dumps(infos, cls=DecimalEncoder),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        return response
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise