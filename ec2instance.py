import boto3
import os
from pathlib import Path
import yaml

#Creates nessacary files needed (utilizes yaml configuration)
dirPath = Path("ec2_files")
if not dirPath.is_dir():
    directory = os.mkdir('ec2_files')

with open('ec2_files/config.yaml') as c:
    config = yaml.load(c, yaml.SafeLoader)
    
yaml.dump(config)

#Establishes ec2 instance
region = config['ec2_instance']['region_id']
instances = config['ec2_instance']['instance_id']
accessKey = config['ec2_instance']['access_key']
secretAccessKey = config['ec2_instance']['secret_access_key']

ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=accessKey, aws_secret_access_key=secretAccessKey)
resource = boto3.resource('ec2', region_name=region, aws_access_key_id=accessKey, aws_secret_access_key=secretAccessKey)

#Checks if running
print("Checking if instance is already running.")
response = ec2.describe_instance_status(InstanceIds=instances, IncludeAllInstances=True)
if response['InstanceStatuses'][0]['InstanceState']['Name'] == 'running':
    print('It is already running!')
else:
    ec2.start_instances(InstanceIds=instances)
    print('Started your instances: ' + str(instances))

for i in resource.instances.all():
    i.wait_until_running()
    i.reload()
    print(i.public_ip_address)

while True:
    cmd = input('Type \'stop\' to shutdown\n')
    if(cmd == 'stop'):
        print('Shutting down!')
        ec2.stop_instances(InstanceIds=instances)
        print('Stopped your instances: ' + str(instances))
        break
    else:
        print('You didn\'t type stop!')