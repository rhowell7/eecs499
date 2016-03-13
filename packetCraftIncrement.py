#!/usr/bin/python

# When scapy sends a SYN packet, the kernel doesn't see it. So when the kernel 
# receives a SYN-ACK back, it typically sends a RST packet, because it didn't
# initiate the conversation.  To supress these RST packets from leaving our box:
# sudo iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
# Install Scapy
# sudo apt-get install python-scapy

from scapy.all import *
import re
import sys
import json

tlsTTL = 3
size250 = re.compile('.*?SIZE.*?', re.DOTALL)
Hello = re.compile('.*Hello.*', re.IGNORECASE)
two50 = re.compile('250.*', re.IGNORECASE)
win = re.compile('.*START ?TLS.*', re.IGNORECASE | re.DOTALL | re.MULTILINE)
error500 = re.compile('500.*', re.IGNORECASE)


"""
Sends a STARTTLS request to mail servers
"""

class PacketCraft:
	def __init__(self, targetIP):
		self.seq = 100
		self.ack = 0
		self.dport = 25
		self.sport = random.randint(1024,65535)
		self.target = targetIP
		self.ehloTTL = 64

	def get220banner(self):
		print "[1. Get 220 Banner for {}]".format(self.target)
		# print self.target
		self.sport = random.randint(1024,65535)		# needs a new port/socket for each loop
		ip = IP(dst=self.target)
		syn = ip/TCP(sport=self.sport, dport=self.dport, flags="S", seq=100)
		synack = sr1(syn, verbose=0, timeout=5)
		if synack is None:
			print 'No response :('
			return 1

		self.ack = synack.seq + 1
		ack = ip/TCP(sport=self.sport, dport=self.dport, flags="A", seq=101, ack=self.ack)
		banner220 = sr1(ack, verbose=0)

		self.ack = self.ack + len(banner220.payload.payload)
		ack = ip/TCP(sport=self.sport, dport=self.dport, flags="A", seq=101, ack=self.ack)
		send(ack, verbose=0)

		print "{}".format(banner220.payload.payload)
		# print "[Got 220 Banner for {}]".format(self.target)
		

	def get250extensions(self):
		print "[2. Get 250 Extensions for {}]".format(self.target)
		# print self.target
		ehlo = IP(dst=self.target, ttl=self.ehloTTL)/TCP(sport=self.sport,dport=self.dport,flags="PA",seq=101,ack=self.ack)/("EHLO ME\r\n")
		send(ehlo, verbose=0)
		extensions = sniff(filter="host {}".format(self.target), count=1)
		
		for x in range(0, 4):
			# ext_packet = str(extensions[0].payload.payload.payload)  # IndexError
			try:
				ext_packet = str(extensions[0].payload.payload.payload)
			except IndexError as e:
				print "IndexError"


			if size250.match(ext_packet):
				# print 'Packet contains 250-SIZE'
				break
			elif error500.match(ext_packet):
				# print 'Packet contains 500'
				break
			elif Hello.match(ext_packet):
				tcp_packet = extensions[0].payload.payload
				self.ack = self.ack + len(tcp_packet.payload)

				ip = IP(dst=self.target)
				ack = ip/TCP(sport=self.sport, dport=self.dport, flags="A", seq=110, ack=self.ack)
				send(ack, verbose=0)
				self.ack = self.ack - len(tcp_packet.payload)
				extensions = sniff(filter="host {}".format(self.target), count=1)
			else:
				print "Packet does not contain SIZE or 500"
				#print ext_packet
				extensions = sniff(filter="host {}".format(self.target), count=1)

		tcp_packet = extensions[0].payload.payload
		self.ack = self.ack + len(tcp_packet.payload)

		ip = IP(dst=self.target)
		ack = ip/TCP(sport=self.sport, dport=self.dport, flags="A", seq=110, ack=self.ack)
		send(ack, verbose=0)

		# print "{}".format(extensions[0].payload.payload.payload)
		# print "[Got 250 Extensions for {}]".format(self.target)
		
	def startTLS(self, tlsTTL):
		print "[3. Try StartTLS for {}]".format(self.target)
		done = re.compile(target)
		# ip = IP(dst=self.target, ttl=tlsTTL)
		# startTLS = ip/TCP(sport=self.sport,dport=self.dport,flags="PA",seq=110,ack=self.ack)/("STARTTLS\r\n")
		# TLSbanner = sr1(startTLS)
		# send(startTLS)
		# TLSbanner = sniff(filter="host {}".format(self.target), count=1)

		for i in range (4, 30):
			# result = smtpConnection.startTLS(i)
			ip = IP(dst=self.target, ttl=i)
			startTLS = ip/TCP(sport=self.sport,dport=self.dport,flags="PA",seq=110,ack=self.ack)/("STARTTLS\r\n")
			TLSbanner = sr1(startTLS, verbose=0, timeout=4)

			# send(startTLS)
			# TLSbanner = sniff(filter="host {}".format(self.target), count=1)

			# print TLSbanner[0].getlayer(IP).src
			# print TLSbanner[0][IP].src
			# serverIP = str(TLSbanner[0].getlayer(IP).src)
			# serverIP = str(TLSbanner[0].src)
			if TLSbanner is None:
				# No reply
				print "None"
				break
			elif done.match(TLSbanner.src):
				print "%d hops away: " % i , TLSbanner.src
				print '{}'.format(TLSbanner.load)
				print "Done"
				# smtpConnection.closeConnection()
				break
			else:
				print "%d hops away: " % i , TLSbanner.src
				# print '{}'.format(TLSbanner.load)
				try:
					print '{}'.format(TLSbanner.load)
			 	except AttributeError as e:
			 		print "AttributeError"

		# self.ack = self.ack + len(TLSbanner[0].payload.payload)
		# ack = TCP(sport=self.sport, dport=self.dport, flags="A", seq=120, ack=self.ack)
		# send(ip/ack)

		# print '[Got STARTTLS Response]'
		# print '{}'.format(TLSbanner.load)
		
		# ip_src=TLSbanner[IP].src
		# f = open('results.{}.txt'.format(str(self.target)), 'a')
		# f.write('Hop {}: '.format(str(tlsTTL)) + 'Banner received from {}'.format(str(ip_src)) + ': {}'.format(TLSbanner.load))
		# f.close()
		# TODO: Print output to JSON dict
		# create object called scan<targetIP>?  New dict for each target IP?
		# scan = {}
		# scan['targetIP'] = self.target
		# scan['hop'] = tlsTTL
		# if error500.match(str(TLSbanner)):
		# 	scan['responseFrom'] = ip_src
		# 	scan['error'] = TLSbanner.load
		# elif win.match(str(TLSbanner)):
		# 	scan['responseFrom'] = ip_src
		# 	scan['pingPacket'] = TLSbanner.load
		# else:
			# startTLS(tlsTTL)	# Make this a recursive call?


		# return str(TLSbanner.load)
		# return str(TLSbanner.src)

	def closeConnection(self):
		print "[4. Closing Connection to {}]".format(self.target)
		FINpacket = IP(dst=self.target)/TCP(sport=self.sport,dport=self.dport,flags="FA",seq=120, ack=self.ack)
		FINACK = sr1(FINpacket, verbose=0, timeout=1)

		packet = IP(dst=self.target)/TCP(sport=self.sport,dport=self.dport,flags="A",seq=121, ack=self.ack+1)
		send(packet, verbose=0)
		print '\n'


with open('ipAddresses.txt') as inFile:
	for line in inFile:
		target = str(line.rstrip('\n'))
		#tlsTTL = 20						# TODO: Optimal TTL to start with based on traceroute?
		win = re.compile('.*START ?TLS*', re.IGNORECASE)
		done = re.compile(target)
		lose = re.compile("5\d\d*")
		result = "test"
		done = 0


		smtpConnection = PacketCraft(target)
		done = smtpConnection.get220banner()
		if done is 1:
			continue
		smtpConnection.get250extensions()
		smtpConnection.startTLS(1)
		smtpConnection.closeConnection()

		# for i in range (4, 28):
		# 	result = smtpConnection.startTLS(i)
		# 	if result is None:
		# 		# No reply
		# 		break
		# 	elif done.match(result):
		# 		print "done"
		# 		smtpConnection.closeConnection()
		# 		break
		# 	else:
		# 		print "%d hops away: " % i , result

		# try:
		# 	result = smtpConnection.startTLS(tlsTTL)
		# except IndexError as e:			# IndexError when the TTL is too short
		# 	print "IndexError"

		# while not lose.match(result):
		# 	tlsTTL = tlsTTL - 1
		# 	# smtpConnection.get220banner()
		# 	# smtpConnection.get250extensions()
		# 	try:
		# 		result = smtpConnection.startTLS(tlsTTL)
		# 	except IndexError as e:
		# 		print "IndexError"

		# 	if win.match(result):
		# 		print "win"
		# 		#smtpConnection.closeConnection()
		# 		# break			# all good servers will end up in this case, along with the bad nodes that strip the STARTTLS
		# 	if lose.match(result):
		# 		print "went too far"
		# 		break			# no good servers will end up in this case, only 500-level errors here, nodes that have already been stripped
