import datetime
import subprocess
from subprocess import Popen
import time

import pytz
import boto3

AWS_ACCESS_KEY_ID='***'
AWS_SECRET_ACCESS_KEY='***'
AWS_DEFAULT_REGION='us-east-2'

JMETER_YOYO_ATTACK_ON = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\jmeter.bat -n -t C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\templates\\Test_Plan_Yoyo_Attack.jmx -l C:\\Users\\Administrator\\Desktop\\results\\attack_results_log.csv -j C:\\Users\\Administrator\\Desktop\\results\\attack_monitor.txt"
JMETER_USER_ON = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\jmeter.bat -n -t C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\templates\\Test_Plan_User.jmx -l C:\\Users\\Administrator\\Desktop\\results\\results_log.csv -j C:\\Users\\Administrator\\Desktop\\results\\monitor.txt"
JMETER_USER_PROB_ON = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\jmeter.bat -n -t C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\templates\\Test_Plan_User.jmx -l C:\\Users\\Administrator\\Desktop\\results\\results_log_{prob}.csv -j C:\\Users\\Administrator\\Desktop\\results\\monitor_{prob}.txt"
JMETER_STOP = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\stoptest.cmd"

g_probnum = 1
stop_ports = {}
stop_ports[4445] = False
stop_ports[4446] = False
stop_ports[4447] = False

def jmeter_user_on(probnum=0):
    returned_value = Popen(JMETER_USER_PROB_ON.format(prob=probnum), shell=True)  # returns the exit code in unix
    print('returned value:', returned_value)
    # Return the port number
    max_port = 0
    for port in stop_ports:
        max_port = port
        if False == stop_ports[port]:
            stop_ports[port] = True
            return port
    stop_ports[max_port+1] = True
    return max_port+1


def jmeter_user_off(port):
    returned_value = Popen(JMETER_STOP+" "+ str(port), shell=True)
    print('returned value:', returned_value)

def jmeter_attack_on():
    returned_value = Popen(JMETER_YOYO_ATTACK_ON, shell=True)  # returns the exit code in unix
    print('returned value:', returned_value)
    # Return the port number
    max_port = 0
    for port in stop_ports:
        max_port = port
        if False == stop_ports[port]:
            stop_ports[port] = True
            return port
    stop_ports[max_port+1] = True
    return max_port+1


def jmeter_attack_off(port):
    returned_value = Popen(JMETER_STOP+" "+ str(port), shell=True)
    print('returned value:', returned_value)

def prob(prob_duration):
    global g_probnum
    port = jmeter_user_on(g_probnum)
    time.sleep(prob_duration)
    jmeter_user_off(port)
    g_probnum = g_probnum + 1


def get_amount_of_running_machines():
    ec2 = boto3.resource('ec2',region_name='us-east-2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'key-name', 'Values':['group7']}])
    return len(list(instances))


def wait_for_steady_state(amount_of_machine_at_steady_state, sleep_between_checks=20, with_prob=False):
    print "     Wait for steady state"
    while True:
        time.sleep(sleep_between_checks)
        current_amount_of_running_machines = get_amount_of_running_machines()
        # print "         current amount of running machines " + str(current_amount_of_running_machines)
        # if amount_of_machine_at_steady_state*2 >= current_amount_of_running_machines:
        if amount_of_machine_at_steady_state == current_amount_of_running_machines:
            print "         Now " + str(
                datetime.datetime.now(pytz.utc)) + ": current amount of running machines " + str(
                current_amount_of_running_machines)
            # wait a littel bit more, just to verify the all scaling activity recieve at the sqs
            time.sleep(sleep_between_checks / 2)
            break
        if (with_prob):
            prob(sleep_between_checks / 2)


def yoyo_attack_with_probs(cycles, sleep_between_cycles):
    attack_log = {}
    for i in range(cycles):
        if i > 0:
            print "wait cool down period of 60 seconds"
            time.sleep(60)
        print "Cycle#" + str(i)
        amount_of_running_machines_before_attack = get_amount_of_running_machines()
        now = datetime.datetime.now()
        port = jmeter_attack_on()
        attack_log[now] = "start"
        print "     Now " + str(now) + ": Wait " + str(sleep_between_cycles) + " seconds"
        current_sleep_between_cycles = sleep_between_cycles
        while current_sleep_between_cycles > 0:
            time_before_prob = time.time()
            prob(10)
            time.sleep(20)
            time_after_prob = time.time()
            current_sleep_between_cycles = current_sleep_between_cycles - (time_before_prob - time_after_prob)

        time.sleep(sleep_between_cycles)
        now = datetime.datetime.now()
        jmeter_attack_off(port)
        attack_log[now] = "stop"
        wait_for_steady_state(amount_of_running_machines_before_attack, 20, True)

    return attack_log


def save_attack_log(attack_log, attack_log_filepath):
    attack_log_data = ""
    for event in sorted(attack_log):
        attack_log_data = attack_log_data + str(event) + "," + attack_log[event]+"\n"

    file = open(attack_log_filepath,'w')
    file.write(attack_log_data)
    file.close()
    print "attack log saved!"


if _name_ == '_main_':
    attack_log = yoyo_attack_with_probs(2, 60*5)
    save_attack_log(attack_log, 'C:\\Users\\Administrator\\Desktop\\results\\attack_log.txt')