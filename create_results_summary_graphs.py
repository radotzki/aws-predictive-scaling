"""
Author: Mor Sides
Purpose: Generate graphs of the machine load and number of machines after executing an attack
Input: The script expects 3 files -
1. JMeter CSV that represents the response time of the requests made
2. AWS scale actions log
3. attack.py logs (start and end times)
"""

import dateutil.parser
import datetime
import pytz
import collections
import numpy
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.ticker import Formatter
import matplotlib.gridspec as gridspec
matplotlib.rcParams.update({'font.size': 14.7})

results_dir = r"C:\Users\Mor\Documents\GitHub\YoYoServer\aws\results\good\\"

class ErrorRowException(Exception):
    pass
class RejectRow(Exception):
    pass

class Row(object):
    def __init__(self, row_data):
        row_arr = row_data.split(',')
        if row_arr[0].isalpha():
            raise ValueError
        if row_arr[7] == "true":
            self.time = datetime.datetime.strptime(row_arr[0], "%Y/%m/%d %H:%M:%S.%f")
            self.response_time = int(row_arr[1])
            self.ip = row_arr[4]
            self.bin = None
        else:
            raise ErrorRowException


    def __str__(self):
        return "time " + str(self.time)

class ErrorRow(object):
    def __init__(self, row_data):
        row_arr = row_data.split(',')
        if row_arr[0].isalpha():
			raise ValueError
        if row_arr[7] == "false":
            if "SocketException" in row_arr[3]:
                raise RejectRow
            elif "NoHttpResponseException" in row_arr[3]:
                self.time = datetime.datetime.strptime(row_arr[0], "%Y/%m/%d %H:%M:%S.%f")
                self.bin = None
            else:
                raise ValueError
        else:
            raise ValueError

    def __str__(self):
        return "time " + str(self.time)

class Bin(object):
    next_id = 0
    def __init__(self,start_time, machines = None):
        self.start_time = start_time
        self.count_errors = 0
        self.error_percent = 0
        self.sum_response = 0
        self.count_response = 0
        self.avg_response = 0
        self.end_time = None
        self.machines = machines
        self.bin_id = Bin.next_id
        Bin.next_id = Bin.next_id + 1
        self.max_response = -1
        self.min_response = -1
        self.prob_delta = 0
        self.is_prob = False

    def set_end_time(self, end_time):
        self.end_time = end_time

    def set_machines(self, machines):
        self.machines = machines

    def __str__(self):
        return_str = "start time: " + str(self.start_time) + "\nend time: " + str(self.end_time)+"\nmachines: " + str(self.machines) + "\nerror percent: " + str(self.error_percent) + "\navg response: " + str(self.avg_response)
        #return_str = "start time: " + str(self.start_time) + "\nend time: " + str(self.end_time)+"\nmachines: " + str(self.machines) +"\nerrors: " + str(self.count_errors) + "\nerror percent: " + str(self.error_percent) + "\nsum response: " + str(self.sum_response) + "\ncount response: " + str(self.count_response)+"\navg response: " + str(self.avg_response)
        return return_str

def parse_scaling_activity(scaling_activity_data):
    history = {}
    parts = scaling_activity_data[1:-1].split(", ")
    for part in parts:
        dateTime = dateutil.parser.parse(part.split(": ")[0][2:-1])
        dateTime = dateTime.replace(tzinfo=None)
        action = part.split(": ")[1][2:-1]
        if action == 'autoscaling:EC2_INSTANCE_LAUNCHING':
            history[dateTime] = 1
        elif action == 'autoscaling:EC2_INSTANCE_TERMINATING':
            history[dateTime] = 2
    return history

def parse_attack_log(attack_log_data):
    attack = {}
    lines = attack_log_data.split('\n')
    for line in lines:
        if line<>"":
            time = datetime.datetime.strptime(line.split(",")[0], "%Y-%m-%d %H:%M:%S.%f")
            if line.split(",")[1] == "start":
                attack[time] = True
            elif line.split(",")[1] == "stop":
                attack[time] = False
    return attack

def parse_results_file(results_file_path):
    value_error = 0
    rows = []
    error_rows = []
    with open(results_file_path, 'r') as results_file_handle:
        for line in results_file_handle:
            try:
                rows.append(Row(line))
            except ErrorRowException:
                try:
                    error_rows.append(ErrorRow(line))
                except RejectRow:
                    pass
            except ValueError:
                value_error = value_error + 1
    print "success: " + str(len(rows)) + " (after parse)"
    print "failure: " + str(len(error_rows)) + " (after parse)"
    return rows,error_rows

def get_first_row_time(rows):
    first_time = datetime.datetime.now()
    for row in rows:
        if row.time < first_time:
            first_time = row.time
    return first_time

def create_bins_by_history(history, start_time, machines = 0):
    bins = []
    index = 0

    #if the history include the scale of the first machine, we don't need to add first bin, it will create by the history
    if machines<>0:
        index = 1
        bins.append(Bin(start_time, machines))

    for date_time in sorted(history):
        if index <> len(history): #index decrease and because we don't want to create bin for the priod after the last terminate
            if history[date_time] == 1:
                machines = machines + 1
            elif history[date_time] == 2:
                machines = machines - 1
            bins.append(Bin(date_time, machines))
        bins[index-1].set_end_time(date_time)
        index = index + 1
    return bins

def update_bins_by_results(bins, results):
    sum = 0
    for row in results:
        for bin in bins:
            if row.time > bin.start_time and row.time <= bin.end_time:
                bin.sum_response = bin.sum_response + row.response_time
                bin.count_response = bin.count_response + 1
                sum = sum+1
                row.bin = bin.bin_id
                if bin.max_response == -1 and bin.min_response == -1:
                    bin.max_response = row.response_time
                    bin.min_response = row.response_time
                elif bin.max_response < row.response_time:
                    bin.max_response = row.response_time
                elif bin.min_response > row.response_time:
                    bin.min_response = row.response_time
                break
    for bin in bins:
        if bin.count_response<> 0:
            bin.avg_response = bin.sum_response/bin.count_response
            bin.prob_delta = bin.max_response - bin.min_response
    print "success: " + str(sum) + " (after update)"
    return bins

def update_bins_by_error_results(bins, error_results):
    sum = 0
    for error_result in error_results:
        for bin in bins:
            if error_result.time > bin.start_time and error_result.time <= bin.end_time:
                bin.count_errors = bin.count_errors + 1
                sum = sum+1
                error_result.bin = bin.bin_id
                break
    for bin in bins:
        if bin.count_errors+ bin.count_response <> 0:
            bin.error_percent = bin.count_errors*100/(bin.count_errors+ bin.count_response)
    print "failure: " + str(sum) + " (after update)"
    return bins

def update_bins_by_history(bins, history, machines = 0):
    last_machine = machines
    for date_time in sorted(history):
        if history[date_time] == 1:
            last_machine = machines
            machines = machines + 1
        elif history[date_time] == 2:
            last_machine = machines
            machines = machines - 1 #TODO

        for bin in bins:
            if date_time > bin.start_time and bin.machines == None:
                bin.machines = last_machine

    return bins

def create_bins_by_time(bin_time_interval_in_seconds, start_time, end_time, machines = 0):
    bins = []
    index = 0
    print start_time, end_time
    current_bin = start_time
    max_time = start_time
    while (current_bin <= end_time):
        bins.append(Bin(current_bin))
        if index <> 0:
            bins[index-1].set_end_time(current_bin)
        current_bin = current_bin + datetime.timedelta(seconds=bin_time_interval_in_seconds)
        index = index + 1
    bins[index-1].set_end_time(end_time)

    return bins

def update_bins_for_probs(bins, bin_duration, interval_between_probs = 180): #=3 min
    if (bin_duration == 0):
        raise Exception
    skip = interval_between_probs / bin_duration
    for i in range(len(bins)):
        if(i%skip == skip-1):
            bins[i].is_prob = True
            print "bin "+  str(i) + " is prob with " + str(bins[i].prob_delta)



    return bins

def create_results_summary(scaling_history_filepath, attack_results_filepath, users_filepath, attack_log_filepath, by_interval = 0, max_time = 0):
    #parse results file with http errors
    results, error_results = parse_results_file(attack_results_filepath)
    if users_filepath <> None:
        users_results, users_error = parse_results_file(users_filepath)

    #parse scaling activity log while machines is on and off
    scaling_activity_data = open(scaling_history_filepath,'r').read()
    history = parse_scaling_activity(scaling_activity_data)

    attack_log_data = open(attack_log_filepath,'r').read()
    attack_log = parse_attack_log(attack_log_data)

    bins = []
    if by_interval == 0:
        bins = create_bins_by_history(history, get_first_row_time(results))
    else:
        bins = create_bins_by_time(by_interval, min(sorted(history)), max(sorted(history)))
        bins = update_bins_by_history(bins, history)

    bins = update_bins_by_results(bins, results)
    if users_filepath <> None:
        bins = update_bins_by_results(bins, users_results)

    bins = update_bins_by_error_results(bins, error_results)
    if users_filepath <> None:
        bins = update_bins_by_error_results(bins, users_error)

    bins = update_bins_for_probs(bins, by_interval)

    if users_filepath <> None:
        for row in users_results:
            if row.bin == None:
                print "problematic row: " + str(row)

    for log in attack_log:
        for bin in bins:
            if log > bin.start_time and log <= bin.end_time:
                attack_log[bin.start_time] = attack_log[log]
                del attack_log[log]

    if max_time != 0:
        print len(bins)
        bins = [x for x in bins if max_time > x.start_time]
        print len(bins)

        print len(attack_log)
        for log in attack_log:
            if log > max_time:
                del log
        print len(attack_log)

    return bins, attack_log


def create_graph_with_prob(bins, attack_log, graph_filepath):
    time_in_seconds = numpy.array([])
    avg_response = numpy.array([])
    error_percent = numpy.array([])
    machines = numpy.array([])
    time_in_seconds_probs = numpy.array([])
    probs = numpy.array([])

    first_date = None
    last_date = None
    for bin in bins:
        if first_date == None:
            first_date = bin.start_time
        if last_date == None or last_date < bin.end_time:
            last_date = bin.end_time
        time_in_seconds = numpy.append(time_in_seconds, int((bin.start_time - first_date).total_seconds()))
        avg_response = numpy.append(avg_response, bin.avg_response)
        error_percent = numpy.append(error_percent, bin.error_percent)
        machines = numpy.append(machines, bin.machines)
        if(bin.is_prob == True):
            time_in_seconds_probs = numpy.append(time_in_seconds_probs, int((bin.start_time - first_date).total_seconds()))
            probs = numpy.append(probs,bin.prob_delta)

    fig = plt.figure()
    gs1 = gridspec.GridSpec(2, 1, height_ratios=[14, 1])
    gs1.update(left=0, right=1, top = 0.40, bottom = 0, hspace=0)
    gs2 = gridspec.GridSpec(2, 1, height_ratios=[14, 1])
    gs2.update(left=0, right=1, top = 1, bottom = 0.6, hspace=0)

    p1 = fig.add_subplot(gs1[0,:])
    p1.plot(time_in_seconds, avg_response, label='Response time')
    p1.set_ylabel("Response time (ms)", color='b')
    p1.tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    p11 = plt.subplot(gs1[1,:], sharex=p1)
    p11.set_ylim(ymin=0,ymax=1)
    p11.set_xlabel("Time(s)\n(b)")
    p11.set_ylabel("On/Off\nattack", rotation='horizontal')
    p11.yaxis.set_label_coords(-0.05, -0.1)
    p11.tick_params(
        axis='y',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        right='off',      # ticks along the bottom edge are off
        left='off',         # ticks along the top edge are off
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off
    #p1.tick_params(
    #    axis='x',          # changes apply to the x-axis
    #    which='both',      # both major and minor ticks are affected
    #    bottom='off',      # ticks along the bottom edge are off
    #    top='off',         # ticks along the top edge are off
    #    labelbottom='off') # labels along the bottom edge are off

    p2 = p1.twinx()
    p2.plot(time_in_seconds, error_percent, 'r--', label='Error percent')
    p2.set_ylabel("Error percent", color='r')
    p2.set_ylim(ymax=100)

    p4 = p1.twinx()
    p4.plot(time_in_seconds_probs, probs, linestyle='None', marker = 'o', color="black", label=r'$\Delta$ Prob')
    p4.tick_params(
        axis='y',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        right='off',      # ticks along the bottom edge are off
        left='off',         # ticks along the top edge are off
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    p3 = fig.add_subplot(gs2[0,:])
    p3.plot(time_in_seconds, machines, label='# of machines')
    p3.set_ylabel("# of machines")
    p3.set_ylim(ymin=0)
    p3.tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    p33 = plt.subplot(gs2[1,:], sharex=p3)
    p33.set_ylim(ymin=0,ymax=1)
    p33.set_xlabel("Time(s)\n(a)")
    p33.set_ylabel("On/Off\nattack", rotation='horizontal')
    p33.yaxis.set_label_coords(-0.05, -0.1)
    p33.tick_params(
        axis='y',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        right='off',      # ticks along the bottom edge are off
        left='off',         # ticks along the top edge are off
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    #p3.tick_params(
    #    axis='x',          # changes apply to the x-axis
    #    which='both',      # both major and minor ticks are affected
    #    bottom='off',      # ticks along the bottom edge are off
    #    top='off',         # ticks along the top edge are off
    #    labelbottom='off') # labels along the bottom edge are off

    x = None
    width = None
    on_attack_exist_in_legend = False
    for event in sorted(attack_log):
        print event
        print attack_log
        print attack_log[event]
        if attack_log[event] == True:
            print event,first_date
            x = int((event - first_date).total_seconds())
        else:
            print event,first_date
            width = int((event - first_date).total_seconds())
            if on_attack_exist_in_legend == False:
                p11.axvspan(x, width, facecolor='g', alpha=0.5, label='On-attack period')
                p33.axvspan(x, width, facecolor='g', alpha=0.5, label='On-attack period')
                on_attack_exist_in_legend = True
            else:
                p11.axvspan(x, width, facecolor='g', alpha=0.5)
                p33.axvspan(x, width, facecolor='g', alpha=0.5)
            x = None
            width = None

    handles_p1, labels_p1 = p1.get_legend_handles_labels()
    handles_p2, labels_p2 = p2.get_legend_handles_labels()
    handles_p11, labels_p11 = p11.get_legend_handles_labels()
    handles_p3, labels_p3 = p3.get_legend_handles_labels()
    handles_p33, labels_p33 = p33.get_legend_handles_labels()
    handles_p4, labels_p4 = p4.get_legend_handles_labels()
    p1.legend(handles_p1+handles_p2+handles_p11+handles_p4, labels_p1+labels_p2+labels_p11+labels_p4, bbox_to_anchor=(0.,1.02, 1., .102), loc=3,ncol=2, mode="expand", borderaxespad=0.)
    p3.legend(handles_p3+handles_p33,labels_p3+labels_p33, bbox_to_anchor=(0., 1.02, 1., .102), loc=3,ncol=2, mode="expand", borderaxespad=0.)


    fig.subplots_adjust(hspace=0.5)
    fig.set_size_inches(10, 8)
    fig.savefig(graph_filepath, bbox_inches='tight', dpi=100)

    #plt.tight_layout()
    #plt.show()

def create_graph(bins, attack_log, graph_filepath):
    time_in_seconds = numpy.array([])
    avg_response = numpy.array([])
    error_percent = numpy.array([])
    machines = numpy.array([])

    first_date = None
    last_date = None
    for bin in bins:
        if first_date == None:
            first_date = bin.start_time
        if last_date == None or last_date < bin.end_time:
            last_date = bin.end_time
        time_in_seconds = numpy.append(time_in_seconds, int((bin.start_time - first_date).total_seconds()))
        avg_response = numpy.append(avg_response, bin.avg_response)
        error_percent = numpy.append(error_percent, bin.error_percent)
        machines = numpy.append(machines, bin.machines)

    fig = plt.figure()
    gs1 = gridspec.GridSpec(2, 1, height_ratios=[14, 1])
    gs1.update(left=0, right=1, top = 0.40, bottom = 0, hspace=0)
    gs2 = gridspec.GridSpec(2, 1, height_ratios=[14, 1])
    gs2.update(left=0, right=1, top = 1, bottom = 0.6, hspace=0)

    p1 = fig.add_subplot(gs1[0,:])
    #p1.plot(time_in_seconds, avg_response, label='System load')
    p1.plot(time_in_seconds, avg_response, label='Response time')
    #p1.set_title('Yo-Yo response time and error percent', y=1)
    #p1.set_ylabel("System load", color='b')
    p1.set_ylabel("Response time (ms)", color='b')
    #p1.set_xlim(xmax=last_date)
    #p1.set_xlabel("Time(s)\n(b)")
    p1.tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    p11 = plt.subplot(gs1[1,:], sharex=p1)
    p11.set_ylim(ymin=0,ymax=1)
    #p11.set_xlim(xmax=last_date)
    p11.set_xlabel("Time(s)\n(b)")
    p11.set_ylabel("On/Off\nattack", rotation='horizontal')
    p11.yaxis.set_label_coords(-0.05, -0.1)
    p11.tick_params(
        axis='y',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        right='off',      # ticks along the bottom edge are off
        left='off',         # ticks along the top edge are off
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off
    #p1.tick_params(
    #    axis='x',          # changes apply to the x-axis
    #    which='both',      # both major and minor ticks are affected
    #    bottom='off',      # ticks along the bottom edge are off
    #    top='off',         # ticks along the top edge are off
    #    labelbottom='off') # labels along the bottom edge are off

    p2 = p1.twinx()
    p2.plot(time_in_seconds, error_percent, 'r--', label='Error percent')
    p2.set_ylabel("Error percent", color='r')
    p2.set_ylim(ymax=100)
    #p2.set_xlim(xmax=last_date)

    p3 = fig.add_subplot(gs2[0,:])
    p3.plot(time_in_seconds, machines, label='# of machines')
    #p3.set_title('Yo-Yo machines count', y=1)
    #p3.set_xlabel("Time(s)\n(a)")
    p3.set_ylabel("# of machines")
    p3.set_ylim(ymin=0)
    #p3.set_xlim(xmax=last_date)
    p3.tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    p33 = plt.subplot(gs2[1,:], sharex=p3)
    p33.set_ylim(ymin=0,ymax=1)
    #p33.set_xlim(xmax=last_date)
    p33.set_xlabel("Time(s)\n(a)")
    p33.set_ylabel("On/Off\nattack", rotation='horizontal')
    p33.yaxis.set_label_coords(-0.05, -0.1)
    p33.tick_params(
        axis='y',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        right='off',      # ticks along the bottom edge are off
        left='off',         # ticks along the top edge are off
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        labeltop='off', labelbottom='off', labelright='off', labelleft='off') # labels along the bottom edge are off

    #p3.tick_params(
    #    axis='x',          # changes apply to the x-axis
    #    which='both',      # both major and minor ticks are affected
    #    bottom='off',      # ticks along the bottom edge are off
    #    top='off',         # ticks along the top edge are off
    #    labelbottom='off') # labels along the bottom edge are off

    x = None
    width = None
    on_attack_exist_in_legend = False
    for event in sorted(attack_log):
        print event
        print attack_log
        print attack_log[event]
        if attack_log[event] == True:
            print event,first_date
            x = int((event - first_date).total_seconds())
        else:
            print event,first_date
            width = int((event - first_date).total_seconds())
            if on_attack_exist_in_legend == False:
                p11.axvspan(x, width, facecolor='g', alpha=0.5, label='On-attack period')
                p33.axvspan(x, width, facecolor='g', alpha=0.5, label='On-attack period')
                on_attack_exist_in_legend = True
            else:
                p11.axvspan(x, width, facecolor='g', alpha=0.5)
                p33.axvspan(x, width, facecolor='g', alpha=0.5)
            x = None
            width = None

    handles_p1, labels_p1 = p1.get_legend_handles_labels()
    handles_p2, labels_p2 = p2.get_legend_handles_labels()
    handles_p11, labels_p11 = p11.get_legend_handles_labels()
    handles_p3, labels_p3 = p3.get_legend_handles_labels()
    handles_p33, labels_p33 = p33.get_legend_handles_labels()
    p1.legend(handles_p1+handles_p2+handles_p11, labels_p1+labels_p2+labels_p11, bbox_to_anchor=(0.,1.02, 1., .102), loc=3,ncol=3, mode="expand", borderaxespad=0.)
    p3.legend(handles_p3+handles_p33,labels_p3+labels_p33, bbox_to_anchor=(0., 1.02, 1., .102), loc=3,ncol=2, mode="expand", borderaxespad=0.)


    fig.subplots_adjust(hspace=0.5)
    fig.set_size_inches(10, 8)
    fig.savefig(graph_filepath, bbox_inches='tight', dpi=100)

    #plt.tight_layout()
    #plt.show()

def main():
    #if len(sys.argv) < 4:
    #    print "usage: convert.py <results_file.csv> <scaling_log.txt> <attack_log.txt>"
    #    exit(1)
    #else:
        #results_file = results_dir+ sys.argv[1]
        file_name = r"20160102_results_134248.csv"
        results_file = results_dir+file_name
        #scaling_log = results_dir+sys.argv[2]
        scaling_log = results_dir+file_name+"_scaling_log.txt"
        #attack_log = results_dir+sys.argv[3]
        attack_log = results_dir+file_name+"_attack_log.txt"

        users_file = results_dir+r"20160102_users_results_134248.csv"
        #users_file = None
        #max_time = datetime.datetime.strptime("2015/12/31 11:00:00.000", "%Y/%m/%d %H:%M:%S.%f")
        bins, attack_log = create_results_summary(scaling_log, results_file, users_file, attack_log, 30)


        #create_graph(bins, attack_log, results_dir+file_name[:-4]+"_7.png")
        create_graph_with_prob(bins, attack_log, results_dir+file_name[:-4]+"_8.png")
        #for bin in bins:
        #    print "---------"
        #    print bin


main()
