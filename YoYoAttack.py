import datetime
import subprocess
import time

import pytz
import boto3

JMETER_YOYO_ATTACK_ON = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\jmeter.bat -n -t C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\templates\\Test_Plan_Yoyo_Attack.jmx -l C:\\Users\\Administrator\\Desktop\\results\\attack_results_log.csv -j C:\\Users\\Administrator\\Desktop\\results\\attack_monitor.txt"
JMETER_USER_ON = "C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\jmeter.bat -n -t C:\\Users\\Administrator\\Desktop\\apache-jmeter-5.1\\apache-jmeter-5.1\\bin\\templates\\Test_Plan_User.jmx -l C:\\Users\\Administrator\\Desktop\\results\\results_log.csv -j C:\\Users\\Administrator\\Desktop\\results\\monitor.txt"

g_probnum = 1


def jmeter_user_on(probnum=0):
    returned_value = subprocess.call(JMETER_YOYO_ATTACK_ON, shell=True)  # returns the exit code in unix
    print('returned value:', returned_value)
    # TODO: Should return the port number
    return returned_value


def jmeter_user_off(port):
    pass


def jmeter_attack_on():
    returned_value = subprocess.call(JMETER_USER_ON, shell=True)  # returns the exit code in unix
    print('returned value:', returned_value)
    # TODO: Should return the port number
    return returned_value


def jmeter_attack_off(port):
    pass


def prob(prob_duration):
    global g_probnum
    port = jmeter_user_on(g_probnum)
    time.sleep(prob_duration)
    jmeter_user_off(port)
    g_probnum = g_probnum + 1


def get_amount_of_running_machines():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'key-name', 'Values':['group7']}])
    return len(instances)


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


if __name__ == '__main__':
    attack_log = yoyo_attack_with_probs(2, 1000)
    save_attack_log(attack_log, 'C:\\Users\\Administrator\\Desktop\\results\\attack_log.txt')
