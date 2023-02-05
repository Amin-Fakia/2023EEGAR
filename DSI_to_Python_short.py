# DSI_to_Python v.1.0 BETA
# The following script can be used to receive DSI-Streamer Data Packets through DSI-Streamer's TCP/IP Protocol.
# It contains an example parser for converting packet bytearrays to their corresponding formats described in the TCP/IP Socket Protocol Documentation (https://wearablesensing.com/downloads/TCPIP%20Support_20190924.zip).
# The script involves opening a server socket on DSI-Streamer and connecting a client socket on Python.

# As of v.1.0, the script outputs EEG data and timestamps to the command window. In addition, the script is able to plot the data in realtime.
# Keep in mind, however, that the plot functionality is only meant as a demonstration and therefore does not adhere to any current standards.
# The plot function plots the signals on one graph, unlabeled.
# To verify correct plotting, one can introduce an artifact in the data and observe its effects on the plots.

# The sample code is not certified to any specific standard. It is not intended for clinical use.
# The sample code and software that makes use of it, should not be used for diagnostic or other clinical purposes.  
# The sample code is intended for research use and is provided on an "AS IS"  basis.  
# WEARABLE SENSING, INCLUDING ITS SUBSIDIARIES, DISCLAIMS ANY AND ALL WARRANTIES
# EXPRESSED, STATUTORY OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT OR THIRD PARTY RIGHTS.
#
# Copyright (c) 2014-2020 Wearable Sensing LLC
# P3,C3,F3,Fz,F4,C4,P4,Cz,CM,A1,Fp1,Fp2,T3,T5,O1,O2,X3,X2,F7,F8,X1,A2,T6,T4,TRG
import time
import socket, struct, time
import numpy as np
import matplotlib.pyplot as plt
import threading
from scipy.signal import butter, lfilter
import matplotlib.image as mpimg
import mne
import vedo
from numpy.fft import rfftfreq
import json
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from functions import getRGB,get_mesh,RBF_Interpolation,get_sensor_3DLocations,findVert
from dsi_24_montage import ch_pos, chnls

mne.set_log_level("ERROR")
plt.style.use('ggplot')
class TCPParser: # The script contains one main class which handles DSI-Streamer data packet parsing.

	def __init__(self, host, port,duration=1):
		"""
			host: string -> localhost
			port: int -> DSI Client Inport
			duration: int -> in seconds
		"""
		self.host = host
		self.port = port
		self.done = False
		self.data_log = b''
		self.latest_packets = []
		self.latest_packet_headers = []
		self.latest_packet_data = np.zeros((1,1))
		self.signal_log = np.zeros((1,20))
		self.time_log = np.zeros((1,20))
		self.montage = []
		self.data = []
		self.fsample = 0
		self.fmains = 0
		self.clean_data = []
		self.packet_size = int(duration * 300)
		self.power_values = []
		headPath = f"./3dmodel/Head.obj"
		self.mesh = get_mesh(headPath)
		self.colors = []
		self.sensor_locations = get_sensor_3DLocations(ch_pos,["TRG"])
		self.channels = ["P3","C3","F3","Fz","F4","C4","P4","Cz","CM",
				"A1","Fp1","Fp2","T3","T5","O1","O2","X3","X2",
				"F7","F8","X1","A2","T6","T4","TRG"]
		self.excl_channels = ["TRG","X1","X2","X3","CM"]
		self.channels_idx = list(range(len(self.channels)))
		#self.excl_channels_idx = []
		for r in self.excl_channels:
			#self.excl_channels_idx.append(self.channels.index(r))
			self.channels_idx.remove(self.channels.index(r))
		

		self.channels_idx_temp = self.channels_idx
		self.channels = [d for i, d in enumerate(self.channels) if d not in self.excl_channels]

		self.sensor_locations_temp = self.sensor_locations
		self.data_thread = threading.Thread(target=self.parse_data)		
		self.sample_freq = 300
		self.fps = 0
		self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		
	
	def parse_data(self):	
		# parse_data() receives DSI-Streamer TCP/IP packets and updates the signal_log and time_log attributes
		# which capture EEG data and time data, respectively, from the last 100 EEG data packets (by default) into a numpy array.
		while not self.done:
			data = self.sock.recv(921600)
			self.data_log += data
			if self.data_log.find(b'@ABCD',0,len(self.data_log)) != -1:										# The script looks for the '@ABCD' header start sequence to find packets.
				for index,packet in enumerate(self.data_log.split(b'@ABCD')[1:]):							# The script then splits the inbound transmission by the header start sequence to collect the individual packets.
					self.latest_packets.append(b'@ABCD' + packet)
				for packet in self.latest_packets:
					self.latest_packet_headers.append(struct.unpack('>BHI',packet[5:12]))
				self.data_log = b''


				for index, packet_header in enumerate(self.latest_packet_headers):		
					# For each packet in the transmission, the script will append the signal data and timestamps to their respective logs.
					if packet_header[0] == 1:
						if np.shape(self.signal_log)[0] == 1:												# The signal_log must be initialized based on the headset and number of available channels.
							self.signal_log = np.zeros((int(len(self.latest_packets[index][23:])/4),20))
							self.time_log = np.zeros((1,20))
							self.latest_packet_data = np.zeros((int(len(self.latest_packets[index][23:])/4),1))

						self.latest_packet_data = np.reshape(struct.unpack('>%df'%(len(self.latest_packets[index][23:])/4),self.latest_packets[index][23:]),(len(self.latest_packet_data),1))
						self.latest_packet_data_timestamp = np.reshape(struct.unpack('>f',self.latest_packets[index][12:16]),(1,1))

						self.signal_log = np.append(self.signal_log,self.latest_packet_data,1)
						self.time_log = np.append(self.time_log,self.latest_packet_data_timestamp,1)
						self.signal_log = self.signal_log[:,-self.packet_size:]
						self.time_log = self.time_log[:,-self.packet_size:]
					## Non-data packet handling
					if packet_header[0] == 5:
						(event_code, event_node) = struct.unpack('>II',self.latest_packets[index][12:20])
						if len(self.latest_packets[index])>24:
							message_length = struct.unpack('>I',self.latest_packets[index][20:24])[0]
						#print("Event code = " + str(event_code) + "  Node = " + str(event_node))
						if event_code == 9:
							montage = self.latest_packets[index][24:24+message_length].decode()
							montage = montage.strip()
							print("Montage = " + montage)
							self.montage = montage.split(',')
						if event_code == 10:
							frequencies = self.latest_packets[index][24:24+message_length].decode()
							#print("Mains,Sample = "+ frequencies)
							mains,sample = frequencies.split(',')
							self.fsample = float(sample)
							self.fmains = float(mains)
			self.latest_packets = []
			self.latest_packet_headers = []

	def set_channels(self,checked):
		self.channels_idx_temp =np.array(self.channels_idx)[checked] # tolist()
		temp_idx = np.array(list(range(len(self.channels))))[checked]
		self.sensor_locations_temp = [b for j,b in enumerate(self.sensor_locations) if j in temp_idx]
		

		
	def log_dsi(self):
		print(len(self.power_values))
		return dict(zip(np.array(self.channels)[self.channels_idx_temp].tolist(),self.power_values))
	# def start_data_parse(self):
	def get_fps(self):
		return self.fps
	def quit(self):
		# self.data_thread.join()
		self.sock.close()
		
	def start_data_processing(self):
		self.sock.connect((self.host,self.port))
		
		self.data_thread.start()
		# data_raw = [d for i, d in enumerate(self.signal_log[:,-self.packet_size:]) if i not in self.excl_channels_idx]
		# self.clean_data = mne.filter.filter_data(data_raw,sfreq=self.sample_freq,l_freq=5,h_freq=12)
		
		sample_freq = 300
		refresh_rate = 1/sample_freq
		

		# N = sample_freq 
		# xf = rfftfreq(N-1, 1 / sample_freq)
		# n_oneside = N//2
 
		while True:
			t1 = time.time()
			data_raw = [d for i, d in enumerate(self.signal_log[:,-self.packet_size:]) if i in self.channels_idx_temp] # O1, O2
			
			try:
				self.clean_data = mne.filter.filter_data(data_raw,sfreq=self.sample_freq,l_freq=5,h_freq=12)
				

				# # yf2 = yf2[:n_oneside]
				ys = np.abs(np.fft.fft(self.clean_data))
				self.power_values = [sum(y) for y in ys]

			
			except Exception as e: pass #pass
			t2 = time.time()
			self.fps = t2-t1
			time.sleep(refresh_rate)

	
	def start_unity_connec(self):
		counter = 0
		test_hostname = '127.0.0.1'
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host,port = socket.gethostbyname(test_hostname ), 25001
		#vedo.settings.allow_interaction = True
		# intrp = RBF_Interpolation(self.mesh,self.sensor_locations,range(20))
		# self.mesh.compute_quality().cmap('jet', input_array=intrp, on="points")
		#proj_snsrs = vedo.Points(findVert(self.sensor_locations_temp,self.mesh),r=12)
		proj_snsrs = vedo.Points(findVert(self.sensor_locations,self.mesh),r=12)
		plot = vedo.Plotter()
		plot.show(self.mesh,proj_snsrs ,interactive= False,bg="black",elevation=-30)
		while counter < 100:
			
			try:
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((host,port))
				
				
				intrp = RBF_Interpolation(self.mesh,self.sensor_locations_temp,self.power_values)
				self.mesh.compute_quality().cmap('jet', input_array=intrp, on="points")
				self.colors = getRGB(self.mesh).tolist()
				

				msg = json.dumps({"mylist": self.colors,"win_idx":0})
				s.sendall(bytes(msg,encoding="utf-8"))
				plot.render()
				#plot.show(self.mesh,proj_snsrs ,interactive= False,bg="black",q=True)
				
				#time.sleep(1/60)
			except Exception as e:
				print("[Unity Socket Error] Connection Failed, retrying.. " + str(e))
				counter+=1
				time.sleep(1)
			
		s.close()
	
		


		
if __name__ == "__main__":

	
	tcp = TCPParser('localhost',9067,1)
	
	
	tcp.real_time()
	
	
	#tcp.real_time()

	
