"""
Author: Mor Sides
Purpose: Wrapper classes for AWS EC2, SQS and Auto Scaling groups
"""
import json
import time

import boto3

global ec2 #ec2 connection

action_duration_in_seconds = 120 # = 2 minutes
auto_scaling_group_lc = "lc-git-MySql3Copy"
auto_scaling_group_name = "my-asg-lbs"

AWS_ACCESS_KEY_ID='***'
AWS_SECRET_ACCESS_KEY='***'
AWS_DEFAULT_REGION='us-east-2'


class ec2(object):
    def __init__(self):
        self.ec2 = boto3.resource('ec2')

    def get_ec2_connection(self):
        return self.ec2

    def get_all_instances(self):
        instances = []
        for instance in self.ec2.instances.all():
            ins = {}
            ins["id"] = instance.id
            ins["name"] = instance.tags[0]['Value']
            ins["state"] = instance.state['Name']
            if(instance.state['Name'] == 'running'):
                ins["ip"] = instance.public_ip_address
            instances.append(ins)
        return instances

    def get_ammount_of_running_machines(self):
        instances = self.ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        ammount = 0
        for instance in instances:
            ammount = ammount+1
        return ammount

    def print_all_instances(self):
        print('instances:')
        for instance in self.ec2.instances.all():
            row = "     " + instance.id + ": " + instance.tags[0]['Value'] + ", " + instance.state['Name']
            if(instance.state['Name'] == 'running'):
                row = row + ", " + instance.public_ip_address
            print row

    def is_machine_running(self,id):
        instances = self.ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for instance in instances:
            if(instance.id == id):
                return True
        return False

    def start_and_get_machine_ip_by_mame(self,attacker_machine_name):
        #get attacker machine id and turn it on
        attackerMachineID = self.get_machine_id_by_name(attacker_machine_name)
        print "Attacker machine id: " + str(attackerMachineID)
        self.turn_on_machine_and_wait(attackerMachineID)

        #get attacker machine ip and create machine_connection object
        ip = self.get_ip_by_id(attackerMachineID)
        return ip

    def get_ip_by_id(self,id):
        for instance in self.ec2.instances.filter(InstanceIds=[id]):
            return instance.public_ip_address

    def get_machine_id_by_name(self,machine_name):
        for instance in self.ec2.instances.filter(Filters=[{'Name': 'tag:Name', 'Values': [machine_name]}]):
            return instance.id

    def turn_on_machine_and_wait(self,id, wait = action_duration_in_seconds):
        isRunnign = self.is_machine_running(id)
        if(not isRunnign):
            print "Turn on machine " + id + " and wait " + str(wait)+" seconds"
            self.ec2.instances.filter(InstanceIds=[id]).start()
        else:
            print "Machine " + id + " is already running"
        while (not isRunnign):
            time.sleep(wait)
            isRunnign = self.is_machine_running(id)
        return

    def stop_machine_by_id(self,id):
        self.ec2.instances.filter(InstanceIds=[id]).stop()

    def stop_all(self):
        instances = self.get_all_instances()
        for instance in instances:
            if instance["state"] == 'running':
                print "Stop instance " + str(instance["id"]) +": " + instance["name"]
                self.stop_machine_by_id(instance["id"])

class autoscaling_group(object):
    def __init__(self, name):
        self.name = name

    def start_and_wait(self, wait = action_duration_in_seconds):
        client = boto3.client('autoscaling')
        response = client.describe_auto_scaling_groups(
                    AutoScalingGroupNames=[
                        self.name,
                    ],
                    #NextToken='string',
                    MaxRecords=1
                    )
        if (response['AutoScalingGroups'][0]['MinSize'] == 0):
            print "Start auto-scaling group: " + self.name + " and wait " + str(wait)+" seconds"
            response = client.update_auto_scaling_group(
                AutoScalingGroupName=self.name,
                LaunchConfigurationName=auto_scaling_group_lc,
                MinSize=1,
                MaxSize=5,
                DesiredCapacity=1,
                DefaultCooldown=60,
                AvailabilityZones=[
                    'us-west-2a',
                ],
                HealthCheckType='ELB',
                HealthCheckGracePeriod=20,
                #PlacementGroup='string',
                VPCZoneIdentifier='subnet-d813a2bd',
                TerminationPolicies=[
                    'OldestInstance',
                ])
            time.sleep(wait)
        else:
            print "Auto-scaling group " + self.name + " is already running"

    def stop_and_wait(self, wait = action_duration_in_seconds):
        client = boto3.client('autoscaling')
        response = client.describe_auto_scaling_groups(
                    AutoScalingGroupNames=[
                        self.name,
                    ],
                    #NextToken='string',
                    MaxRecords=1
                    )
        if (response['AutoScalingGroups'][0]['MinSize'] <> 0):
            print "Stop auto-scaling group: " + self.name + " and wait " + str(wait)+" seconds"
            response = client.update_auto_scaling_group(
                AutoScalingGroupName=self.name,
                LaunchConfigurationName=auto_scaling_group_lc,
                MinSize=0,
                MaxSize=5,
                DesiredCapacity=0,
                DefaultCooldown=60,
                AvailabilityZones=[
                    'us-west-2a',
                ],
                HealthCheckType='ELB',
                HealthCheckGracePeriod=20,
                #PlacementGroup='string',
                VPCZoneIdentifier='subnet-d813a2bd',
                TerminationPolicies=[
                    'OldestInstance',
                ])
            time.sleep(wait)
        else:
            print "Auto-scaling group " + self.name + " is already stopped and not running"

    def chage_cooldown(self,cooldown):
        client = boto3.client('autoscaling')
        response = client.describe_auto_scaling_groups(
                    AutoScalingGroupNames=[
                        self.name,
                    ],
                    #NextToken='string',
                    MaxRecords=1
                    )
        response = client.update_auto_scaling_group(
            AutoScalingGroupName=self.name,
            LaunchConfigurationName=auto_scaling_group_lc,
            MinSize=response['AutoScalingGroups'][0]['MinSize'],
            MaxSize=response['AutoScalingGroups'][0]['MaxSize'],
            DesiredCapacity=response['AutoScalingGroups'][0]['DesiredCapacity'],
            DefaultCooldown=cooldown,
            AvailabilityZones=[
                'us-west-2a',
            ],
            HealthCheckType='ELB',
            HealthCheckGracePeriod=20,
            #PlacementGroup='string',
            VPCZoneIdentifier='subnet-d813a2bd',
            TerminationPolicies=[
                'OldestInstance',
            ])
class sqs(object):
    def __init__(self, url):
        self.sqs = boto3.resource('sqs', region_name=AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        self.queue = self.sqs.Queue(url)

    def receive_messages(self, max_queue_messages = 10):
        message_bodies = []
        while True:
            messages_to_delete = []
            for message in self.queue.receive_messages(MaxNumberOfMessages=max_queue_messages):
                # process message body
                body = json.loads(message.body)
                #print message.body
                #inner_body = json.loads(body[u'Message'])
                message_bodies.append(body)

                # add message to delete
                messages_to_delete.append({
                    'Id': message.message_id,
                    'ReceiptHandle': message.receipt_handle
                })

            # if you don't receive any notifications the
            # messages_to_delete list will be empty
            if len(messages_to_delete) == 0:
                break
            # delete messages to remove them from SQS queue handle any errors
            else:
                delete_response = self.queue.delete_messages(Entries=messages_to_delete)
        return message_bodies

    def clear_queue(self):
        self.queue.purge()

    def save_scaling_history(self, file_name_to_save):
        file = open(file_name_to_save,"w")

        messages = self.receive_messages()
        history = {}
        for message in messages:
            #save the scaling activity event and time
            history[message["Time"]] = message["LifecycleTransition"]
        file.write(json.dumps(history))
        file.close()
        print "scaling history saved!"

def shutdown_all_system():
    ec2obj = ec2()
    asg = autoscaling_group(auto_scaling_group_name)
    asg.stop_and_wait()
    ec2obj.stop_all()


