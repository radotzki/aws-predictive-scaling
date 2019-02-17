"""
Author: Mor Sides
Purpose: Connect with the attacker machine (Windows server with JMeter installed) and manage the attack
Description:
- Open an SSH connection
- Support to attack modes for JMeter - User and YoYo
- Copies the JMeter logs when done using SFTP
"""
import paramiko
import utils
import time
import datetime

user1_username = "root"
user1_password = "myRootPassword"
user1_key_file = r"C:\tools\amazon\root_ppk_as_openssh"

command_line_prefix = r"cmd.exe /c "

jmeter_dir = r"C:\Users\Administrator\Desktop\apache-jmeter-2.12\apache-jmeter-2.12\bin\\"
jmeter_bat = "jmeter.bat"
jmeter_config = "HTTP_Request.jmx"
jmeter_user_config = "HTTP_User_Request.jmx"
jmeter_stop = "stoptest.cmd"
jmeter_results_dir = r"C:\Users\Administrator\Desktop\results\\"

class machine_connection(object):
    def __init__(self, ip,results_directory_name = None,results_file_name = None):
        self.ip = ip
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.isConnected = False
        self.stop_ports = {}
        self.stop_ports[4445]  = False
        self.stop_ports[4446]  = False
        self.stop_ports[4447]  = False
        if results_directory_name <> None and results_file_name <> None:
            self.results_directory_name = results_directory_name
            self.results_file_name = results_file_name#jmeter_results_dir+results_directory_name+"\\"+results_file_name
            self.sftp_results_file = r"./"+results_directory_name+r"/"+results_file_name
            self.sftp_users_results_file = r"./"+results_directory_name+r"/users_@_"+results_file_name

    def __del__(self):
        self.client.close()

    def connect(self, timeout=None):
        try:
            self.client.connect(self.ip, username=user1_username, password=user1_password, key_filename=user1_key_file, timeout=timeout)
            self.isConnected = True
            return True
        except:
            return False

    def exec_command_non_blocking(self, cmd):
        if not self.isConnected:
            self.connect()
        try:
            stdin, stdout, stderr = self.client.exec_command(command_line_prefix + cmd)
            return
        except:
            print  "ExecuteCommandException!"
            raise

    def exec_command_blocking(self, cmd):
        if not self.isConnected:
            self.connect()
        try:
            stdin, stdout, stderr = self.client.exec_command(command_line_prefix + cmd)
            data = stdout.readlines()
            return data
        except Exception as e:
            print "ExecuteCommandException!"
            raise e

    def create_results_directory(self):
        print "Create results directory " + self.results_directory_name
        cmd = r"mkdir " + jmeter_results_dir + self.results_directory_name
        self.exec_command_blocking(cmd)

    def get_datetime(self):
        cmd = r"C:\Users\Administrator\Desktop\date.bat"
        time = self.exec_command_blocking(cmd)
        return datetime.datetime.strptime(time[0][:-2], "%Y-%m-%d %H:%M:%S.%f")

    def yoyo_on_attack(self):
        print "Start attack"
        cmd = jmeter_dir+jmeter_bat + r" -n -t " + jmeter_dir+jmeter_config+ r" -l " + jmeter_results_dir+self.results_directory_name+"\\"+self.results_file_name +" -j "+jmeter_results_dir+self.results_directory_name+"\monitor.txt"
        self.exec_command_non_blocking(cmd)
        max_port = 0
        for port in self.stop_ports:
            max_port = port
            if False == self.stop_ports[port]:
                self.stop_ports[port] = True
                return port
        self.stop_ports[max_port+1] = True
        return max_port+1

    def yoyo_off_attack(self, port):
        print "Stop attack"
        cmd = jmeter_dir+jmeter_stop+" "+ str(port)
        self.exec_command_non_blocking(cmd)
        self.stop_ports[port] = False

    def jmeter_user_on(self, probnum = 0):
        print "Start Users"
        cmd = jmeter_dir+jmeter_bat + r" -n -t " + jmeter_dir+jmeter_user_config+ r" -l " + jmeter_results_dir+self.results_directory_name+"\\users_"+str(probnum)+"_"+self.results_file_name +" -j "+jmeter_results_dir+self.results_directory_name+"\users_monitor.txt"
        self.exec_command_non_blocking(cmd)
        max_port = 0
        for port in self.stop_ports:
            max_port = port
            if False == self.stop_ports[port]:
                self.stop_ports[port] = True
                return port
        self.stop_ports[max_port+1] = True
        return max_port+1

    def jmeter_user_off(self, port):
        print "Stop Users"
        cmd = jmeter_dir+jmeter_stop+" "+ str(port)
        self.exec_command_non_blocking(cmd)
        self.stop_ports[port] = False

    def copy_file(self, remote_file_path, local_file_path):
        print "copy_file, remote: " +remote_file_path
        print "copy_file, local: " +local_file_path
        if(not self.isConnected):
            self.connect()
        sftp = self.client.open_sftp()

        try:
            #print sftp.stat('./20151227//results_184216.csv')
            sftp.get(remote_file_path,local_file_path)
        except:
            print remote_file_path + " not exists or permission denied!"

        sftp.close()

    def dir_list(self, path = "."):
        if(not self.isConnected):
            self.connect()
        sftp = self.client.open_sftp()

        try:
            print sftp.listdir(path)
        except:
            print "dir_list error"

        sftp.close()

    def file_stat(self, file_path):
        if(not self.isConnected):
            self.connect()
        sftp = self.client.open_sftp()

        try:
            print sftp.stat(file_path)
        except:
            print file_path + " error"

        sftp.close()

    def copy_results_file(self, local_results_dir):
        print "copy_results_file, local: " +local_results_dir
        self.copy_file(self.sftp_results_file, local_results_dir+r"\\"+self.results_directory_name+"_"+self.results_file_name)

    def copy_users_results_file(self, local_results_dir, probnum = 0):
        print "copy_results_file, local: " +local_results_dir
        self.copy_file(self.sftp_users_results_file.replace("@", str(probnum)), local_results_dir+r"\\"+self.results_directory_name+"_users_"+str(probnum)+"_"+self.results_file_name)
