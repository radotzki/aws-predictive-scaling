"""
Author: Mor Sides
Purpose: Simulates a YoYo attack on an auto scaling group of EC2
Description:
1. Purge the SQS queue to keep track of the scaling actions
2. Initiate the auto scaling group (set minimum size to 1, etc.)
3. Connect to the attacker machine (Windows server with JMeter installed)
4. Simulate normal traffic
5. Simulate YoYo attack
6. Dump logs from JMeter, SQS and the script itself
"""
import boto3
import time
import os
import datetime
import paramiko
import pytz
import utils
import machine_connection

global ec2
client_machine_name = "windowsNotAutoScale"

auto_scaling_group_name = "my-asg-lbs"
sqs_url='https://us-west-2.queue.amazonaws.com/839913665213/ScalingActivityQueue'

local_results_dir = r"C:\Users\Mor\Documents\GitHub\YoYoServer\aws\results"

g_probnum = 1

def create_file_name():
    return time.strftime("results_%H%M%S.csv")
def create_directory_name():
    return time.strftime("%Y%m%d")

results_directory_name  =  create_directory_name()
results_file_name = create_file_name()

def yoyo_attack(attackMachine, cycles, sleep_between_cycles, group):
    global ec2
    attack_log = {}
    for i in range(cycles):
        if i>0:
            print "wait cool down period of 60 seconds"
            time.sleep(60)
        print "Cycle#"+str(i)
        ammount_of_running_machines_before_attack = ec2.get_ammount_of_running_machines()
        now = attackMachine.get_datetime()
        port = attackMachine.yoyo_on_attack()
        #group.chage_cooldown(1300)
        attack_log[now] = "start"
        print "     Now " + str(now) + ": Wait "+ str(sleep_between_cycles) + " seconds"
        time.sleep(sleep_between_cycles)
        now = attackMachine.get_datetime()
        attackMachine.yoyo_off_attack(port)
        #group.chage_cooldown(60)
        attack_log[now] = "stop"
        wait_for_steady_state(ammount_of_running_machines_before_attack)
        #a = raw_input("Press Enter to continue next cycle...")
    return attack_log

def prob(attackMachine, prob_duration):
    global g_probnum
    port = attackMachine.jmeter_user_on(g_probnum)
    time.sleep(prob_duration)
    attackMachine.jmeter_user_off(port)
    attackMachine.copy_users_results_file(local_results_dir, g_probnum)
    g_probnum = g_probnum+1

def yoyo_attack_with_probs(attackMachine, cycles, sleep_between_cycles):
    global ec2
    attack_log = {}
    for i in range(cycles):
        if i>0:
            print "wait cool down period of 60 seconds"
            time.sleep(60)
        print "Cycle#"+str(i)
        ammount_of_running_machines_before_attack = ec2.get_ammount_of_running_machines()
        now = attackMachine.get_datetime()
        port = attackMachine.yoyo_on_attack()
        attack_log[now] = "start"
        print "     Now " + str(now) + ": Wait "+ str(sleep_between_cycles) + " seconds"
        current_sleep_between_cycles = sleep_between_cycles
        while current_sleep_between_cycles > 0:
            time_before_prob = time.time()
            prob(attackMachine, 10)
            time.sleep(20)
            time_after_prob = time.time()
            current_sleep_between_cycles = current_sleep_between_cycles - (time_before_prob - time_after_prob)

        time.sleep(sleep_between_cycles)
        now = attackMachine.get_datetime()
        attackMachine.yoyo_off_attack(port)
        attack_log[now] = "stop"
        wait_for_steady_state(ammount_of_running_machines_before_attack,20, True, attackMachine)

    return attack_log

def detect_scale_state_cycle(attackMachine, cycles):
    global ec2, g_probnum
    attack_log = {}

    ammount_of_running_machines_before_attack = ec2.get_ammount_of_running_machines()

    print "probnum: " + str(g_probnum)
    prob(attackMachine,20, False)

    print "     prob finish, sleep 20"
    time.sleep(20)

    print "probnum: " + str(g_probnum)
    prob(attackMachine, 20, False)

    print "     prob finish, sleep 20"
    time.sleep(20)

    for i in range(cycles):
        print "now start attack!"
        now = attackMachine.get_datetime()
        port = attackMachine.yoyo_on_attack()
        attack_log[now] = "start"
        time.sleep(5)

        print "send probes:"
        stop = False
        while(not stop):
            print "     probnum: " + str(g_probnum)
            prob(attackMachine, 20)
            time.sleep(5)

            current_amount_of_running_machines = ec2.get_ammount_of_running_machines()
            if(current_amount_of_running_machines == 5):
                stop = True
            print "current_amount_of_running_machines: " + str(current_amount_of_running_machines)

        print "now stop attack!"
        now = attackMachine.get_datetime()
        attackMachine.yoyo_off_attack(port)
        attack_log[now] = "stop"

        print "send probes:"
        stop = False
        while(not stop):
            print "     probnum: " + str(g_probnum)
            prob(attackMachine,20)
            time.sleep(5)

            current_amount_of_running_machines = ec2.get_ammount_of_running_machines()
            if(current_amount_of_running_machines == ammount_of_running_machines_before_attack):
                stop = True
            print "current_amount_of_running_machines: " + str(current_amount_of_running_machines)

        print "finish cycle!"

    return attack_log


def wait_for_steady_state(amount_of_machine_at_steady_state, sleep_between_checks = 20, with_prob = False, attackMachine = None):
    global ec2

    print "     Wait for steady state"
    while True:
        time.sleep(sleep_between_checks)
        current_amount_of_running_machines = ec2.get_ammount_of_running_machines()
        #print "         current amount of running machines " + str(current_amount_of_running_machines)
        #if amount_of_machine_at_steady_state*2 >= current_amount_of_running_machines:
        if amount_of_machine_at_steady_state == current_amount_of_running_machines:
            print "         Now " + str(datetime.datetime.now(pytz.utc)) + ": current amount of running machines " + str(current_amount_of_running_machines)
            #wait a littel bit more, just to verify the all scaling activity recieve at the sqs
            time.sleep(sleep_between_checks/2)
            break
        if(with_prob):
            prob(attackMachine, sleep_between_checks/2)

def save_attack_log(attack_log, attack_log_filepath):
    attack_log_data = ""
    for event in sorted(attack_log):
        attack_log_data = attack_log_data + str(event) + "," + attack_log[event]+"\n"

    file = open(attack_log_filepath,'w')
    file.write(attack_log_data)
    file.close
    print "attack log saved!"

def main():
        global ec2
        #init ec2
        ec2 = utils.ec2()

    #try:
        #validate queue is empty
        sqs = utils.sqs(sqs_url)
        sqs.clear_queue()

        #start auto-scaling group
        group = utils.autoscaling_group(auto_scaling_group_name)
        group.start_and_wait()

        #start attacker machine, connect and create results directory
        attacker_ip = ec2.start_and_get_machine_ip_by_mame(client_machine_name)
        attacker = machine_connection.machine_connection(attacker_ip,results_directory_name,results_file_name)
        attacker.connect()
        attacker.create_results_directory()

        #start notmal users
        user_port = attacker.jmeter_user_on()
        time.sleep(120)

        #start attack
        #attack_log = yoyo_attack(attacker, 2,1000, group)

        #start test for probe
        #attack_log = detect_scale_state_cycle(attacker, 2)

        attack_log = yoyo_attack_with_probs(attacker, 2,1000)

        #stop normal users
        attacker.jmeter_user_off(user_port)

        #collect results
        attacker.copy_results_file(local_results_dir)
        attacker.copy_users_results_file(local_results_dir)

        #shutdown all system
        utils.shutdown_all_system()

        #continue collect results
        sqs.save_scaling_history(local_results_dir+r"\\"+results_directory_name+"_"+results_file_name+"_scaling_log.json")
        save_attack_log(attack_log, local_results_dir+r"\\"+results_directory_name+"_"+results_file_name+"_attack_log.txt")

    #except:
    #    print "Error!"

main()
