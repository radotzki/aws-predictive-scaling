#!/usr/bin/python

"""
Author: Mor Sides
Purpose: Simple HTTP Server that does a simple math calculation
"""

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import socket # for server ip
import hashlib #for md5 calculator
import cgi
import sys

PORT_NUMBER = 5005
BUFFER_SIZE = 1024

db_log_host_name = "log.cl7siflajy7i.us-west-2.rds.amazonaws.com"
db_log_user = "admin"
db_log_password = "admin1234"
db_log_name = "Log"
db_log_table_name = "echo_log"

#global
server_ip = socket.gethostbyname(socket.gethostname())
local = False
if len(sys.argv) > 1:
	local = True

'''
####################################################################
###### use case of using sql db which save files with md5  #########
####################################################################
if not local:
	import MySQLdb
	
class MySQLLogdb( object ):
    def __init__( self ):
        self.db   = None
        self.cursor = None
        # open connection to log db
        self.db = MySQLdb.connect(db_log_host_name, db_log_user, db_log_password, db_log_name)
        # prepare a cursor object using cursor() method
        self.cursor = self.db.cursor ()

    def __del__( self ):
        if self.cursor is not None:
            self.cursor.close()
        if self.db is not None:
            self.db.close()

    def write2log( self , act, clientIP, doCommit = False, data = None):
        #act:	1 - client connect
		#		2 - client send file
		#		3 - client disconnect
		#		4 - server up
        insertQuery = "INSERT INTO "+db_log_table_name+" (timestamp, event_type, server_ip, client_ip, data) VALUES (NOW(6), " + str(act) + ", '" + server_ip + "','" + clientIP
        if data == None:
            insertQuery = insertQuery + "', NULL);"
        else:
            insertQuery = insertQuery + "', '" + data + "');"
        self.cursor.execute(insertQuery)
	
        if(doCommit or data != None):
            self.db.commit()
			
    def updateFileNameWithMd5( self, clientIP, filename, md5):
        selectQuery = "SELECT * from " + db_md5_table_name + " where client_ip = '" + clientIP + "' and filename = '" + filename + "';"
        count = self.cursor.execute(selectQuery)
        if count == 0:
            self.addMd5(clientIP, filename, md5)
            print "New file"
            return 1
        else:
            row = self.cursor.fetchone()
            if row[2] == md5:
                self.updateMd5(clientIP, filename, md5, row[3]+1)
                print "Old file, old MD5, New count=" + str(row[3]+1)
                return row[3]+1
            else:
                self.deleteMd5(clientIP, filename)
                self.addMd5(clientIP, filename, md5)
                print "Old file, New MD5"
                return 1
	
    def addMd5(self, clientIP, filename, md5):
        insertQuery = "INSERT INTO " + db_md5_table_name + " (client_ip, filename , md5 , count) VALUES ('" + clientIP + "', '" + filename + "', '" + md5 + "', 1);"
        self.cursor.execute(insertQuery)
	
    def updateMd5(self, clientIP, filename, md5, count):
        updateQuery = "UPDATE " + db_md5_table_name + " SET count=" + str(count) + " WHERE client_ip='" + clientIP + "' and filename = '" + filename + "';"
        self.cursor.execute(updateQuery)
		
    def deleteMd5(self, clientIP, filename):
        deleteQuery = "DELETE FROM " + db_md5_table_name + " WHERE client_ip='" + clientIP + "' and filename = '" + filename + "';"
        self.cursor.execute(deleteQuery)
		
    def rollback( self ):
        self.db.rollback()
        
###########################################################################
###### end of use case of using sql db which save files with md5  #########
###########################################################################
'''

#This class will handles any incoming request
class myHandler(BaseHTTPRequestHandler):
	#Handler for the GET requests
	def do_GET(self):
		self.send_response(200)
		self.send_header('Content-type','text/html')
		self.end_headers()
		self.wfile.write("Hello World! I'm running...")
		return

	def do_POST(self):
		try:
			#recieve the file metadata
			#file_name = self.headers['Content-file-name']
			length = int(self.headers['Content-length'])

			#recieve the file and calc md5
			#md5Calculator = hashlib.md5()
			#index = 0
			#while index < length:
			#	amount = min(length,index+BUFFER_SIZE) - index
			#	newdata = self.rfile.read(amount)
			#	md5Calculator.update(newdata)
			#	index = index + amount
			#md5 = md5Calculator.hexdigest()

			# Begin the response
			self.send_response(200)
			#self.send_header('Content-md5',md5)
			#self.send_header('Content-file-name', file_name)
			self.send_header('2**2**2**2**2', 2**2**2**2**2) #simple server with mathematic calculation
			self.send_header('Server-ip',server_ip)
			self.send_header('Client-ip',str(self.client_address))
			self.end_headers()
		except:
			print ":("
			pass

class YoYoServer( object ):
	#def __init__( self ):
		#if not local:
		#	self.logdb = MySQLLogdb()
		#	self.logdb.write2log(4, "", True);

	def run( self ):
		try:
			#Create a web server and define the handler to manage the
			#incoming request
			server = HTTPServer(('', PORT_NUMBER), myHandler)
			print 'Started httpserver on port ' , PORT_NUMBER

			#Wait forever for incoming htto requests
			server.serve_forever()

		except KeyboardInterrupt:
			print '^C received, shutting down the web server'
			server.socket.close()

# main
if __name__ == "__main__":
	server = YoYoServer()
	server.run()
