import boto3
import os
import sys
from pathlib import Path
import yaml
import time
import paramiko

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
ssh_user = config['ec2_instance']['ec2_user']
keyfile = config['ssh']['keyfile']
minRAM = config['mc']['xms']
maxRAM = config['mc']['xmx']


ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=accessKey, aws_secret_access_key=secretAccessKey)
resource = boto3.resource('ec2', region_name=region, aws_access_key_id=accessKey, aws_secret_access_key=secretAccessKey)

#Checks if running
response = ec2.describe_instance_status(InstanceIds=instances, IncludeAllInstances=True)
if response['InstanceStatuses'][0]['InstanceState']['Name'] == 'running':
    print('It is already running!')
    starting = False
else:
    try:
        ec2.start_instances(InstanceIds=instances)
        print('Starting your instances: {}'.format(instances))
        starting = True
    except:
        print('The instance seems to not be in a running state pelase wait a few seconds and try again\nOr there might be issues with the server')
        sys.exit()

#Function to retry connections
def ssh_connect_attempt(ssh, ip_address, retries):
    if retries > 3:
        print('Couldn\'t connect!')
        ec2.stop_instances(InstanceIds=instances)
        sys.exit()
    key = paramiko.RSAKey.from_private_key_file(
        './ec2_files/' + keyfile)
    interval = 5
    try:
        retries += 1
        print('SSH into the instance: {}'.format(ip_address))
        ssh.connect(hostname=ip_address,
            username='ec2-user', pkey=key)
    except Exception as e:
        time.sleep(interval)
        print('Retrying SSH connection to {}'.format(ip_address))
        ssh_connect_attempt(ssh, ip_address, retries)

#Get instance info
instance = resource.Instance(id=instances[0])
instance.wait_until_running()
current_instance = list(resource.instances.filter(InstanceIds=[instances[0]]))
ip_address = current_instance[0].public_ip_address
print('Your instance IP: {}'.format(ip_address))

#Run commands to build server
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
if(starting):
    print('Setting up the necassary files!')
    ssh_connect_attempt(ssh, ip_address, 0)
    stdin, stdout, stderr = ssh.exec_command(
        'sudo mfks.ext4 -F -E nodiscard /dev/nvme1n1\nsudo mkdir /data\nsudo mount /dev/nvme1n1 /data\nsudo mkdir /data/server\nsudo aws s3 sync s3://rad-server-files ~\nsudo mv ~/server.zip /data\nsudo unzip /data/server.zip -d /data/server\nscreen -dmS minecraft sudo java -Xmx' + maxRAM + ' -Xms' + minRAM + ' -XX:PermSize=512m -jar server.jar nogui'
    )
    ssh.close()
    print('Please wait for the server to finsih starting!')

#Asks to stop server
print('\n\nThe IP is {}'.format(ip_address) + '\n\n')
while True:
    cmd = input('Type \'stop\' to shutdown OR type \'stopmc\' to only shutdown the Minecraft server!\n')
    if(cmd == 'stop'):
        print('Shutting down Minecraft Server!')

        ssh_connect_attempt(ssh, ip_address, 0)

        stdin, stdout, stderr = ssh.exec_command('screen -S minecraft -p 0 -X stuff "stop^M"\nsudo rm -r /data/server.zip\ncd /data/server/\nsudo zip -r server.zip .\nsudo mv /data/server/server.zip ~\nsudo aws s3 cp ~/server.zip s3://rad-server-files\nsudo rm -r /data/server')
        ssh.close()
        print('Shutting down instances!')
        ec2.stop_instances(InstanceIds=instances)
        print('Stopped your instances: {}'.format(instances))
        break
    else:
        print('You didn\'t type stop!')
    