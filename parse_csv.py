import gzip
import sys
import bisect
import functools

if len(sys.argv)!=4:
	print(sys.argv[0],"time[0/1] mosi.csv spi_enable.csv")
	sys.exit(1)

print_time=int(sys.argv[1])==1
fn_mosi=sys.argv[2]
fn_spienable=sys.argv[3]

spi_enable=[]
f_spienable=gzip.open(fn_spienable,'r')
f_spienable.readline()
for line in f_spienable:
	line=line.decode('utf8').strip()
	time_str,spi_enable_state=line.split(',')
	spi_enable.append((float(time_str),spi_enable_state))

f=gzip.open(fn_mosi,'r')
f.readline() # header

line=f.readline()
prev_c="START"

payload_width=0
address_width=0
channel=0

register_table={
	'CONFIG':(0x00,1),
	'EN_ENHANCED':(0x01,1),
	'EN_RXADDR':(0x02,1),
	'SETUP_AW':(0x03,1),
	'SETUP_RETR':(0x04,1),
	'RF_CH':(0x05,1),
	'RF_SETUP':(0x06,1),
	'STATUS':(0x07,1),
	'OBSERVE_TX':(0x08,1),
	'DATAOUT':(0x09,1),
	'RX_ADDR_P0':(0x0A,5),
	'RX_ADDR_P1':(0x0B,5),
	'RX_ADDR_P2':(0x0C,1),
	'RX_ADDR_P3':(0x0D,1),
	'RX_ADDR_P4':(0x0E,1),
	'RX_ADDR_P5':(0x0F,1),
	'TX_ADDR':(0x10,5),
	'RX_PW_P0':(0x11,1),
	'RX_PW_P1':(0x12,1),
	'RX_PW_P2':(0x13,1),
	'RX_PW_P3':(0x14,1),
	'RX_PW_P4':(0x15,1),
	'RX_PW_P5':(0x16,1),
	'FIFO_STATUS':(0x17,1),
	'DEMOD_CAL':(0x19,1),
	'RF_CAL2':(0x1A,1),
	'DEM_CAL2':(0x1B,3),
	'DYNPD':(0x1C,1),
	'FEATURE':(0x1D,1),
	'RF_CAL':(0x1E,3),
	'BB_CAL':(0x1F,5)}
register_id_table={ v[0]:(k,v[1]) for k,v in register_table.items()}
	

tx_payload_map={
	'lCtrl_v':{'type':'range','min':0x00,'max':0xfa,'idle':0x7d,'byte':4},
	'lCtrl_h':{'type':'range','min':0x00,'max':0xfa,'idle':0x7d,'byte':5},
	'rCtrl_v':{'type':'range','min':0x00,'max':0xfa,'idle':0x7d,'byte':6},
	'rCtrl_h':{'type':'range','min':0x00,'max':0xfa,'idle':0x7d,'byte':7},
	'channel_pulse':{'type':'indicator','byte':12,'bit':6},
	'gpshome_b':{'type':'indicator','byte':12,'bit':5},
	'picture_b':{'type':'indicator','byte':12,'bit':0},
	'high_low_b':{'type':'indicator','byte':12,'bit':1},
	'takeoff_b':{'type':'indicator','byte':13,'bit':4},
	'lock_b':{'type':'indicator','byte':13,'bit':6},
	'gpsen_b':{'type':'indicator','byte':14,'bit':6},
}



def read_bytes(f,n,timeout=0.0001):
	bytes_=[]
	prev_time=-1
	while n>0:
		prev_pos=f.tell()
		line=f.readline().decode('utf8').strip()
		time_str,id_str,mosi_str,miso_str = line.split(',')
		time=float(time_str)
		if prev_time<0:
			prev_time=time
		else:
			a=bisect.bisect_left(spi_enable,(time,0))
			b=bisect.bisect_left(spi_enable,(prev_time,0))
			if a!=b or time-prev_time>timeout:
				#return what we have
				f.seek(prev_pos)
				break
		prev_time=time
		mosi_val=int(mosi_str,16)
		bytes_.append(mosi_val)
		n-=1
	#bytes_.reverse()
	return bytes_

def to_hex(s):
	return "0x"+".".join([ hex(x)[2:] for x in s ])


def compute_checksum_tx(s,key):
	#this checsum is the first byte of a radio message
	checksum=functools.reduce(lambda a,b : a ^ b , s[1:]+[key])
	return checksum

def compute_checksum_rx(s,key):
	#this checsum is the first byte of a radio message
	checksum=functools.reduce(lambda a,b : a + b , s[1:]+[key])
	return checksum&0xff

class XN297:
	registers={ } #TODO add defaults

	@property 
	def address_width(self):
		return {0:-1, 1:3,
			2:4, 3:5}[self.registers['SETUP_AW'][0] & 0x03]
	@property 
	def channel(self):
		return self.registers['RF_CH'][0]

	@property 
	def payload_length(self):
		return {3:64,0:32}[self.registers['FEATURE'][0]&0x18]

	def r_register(self,register,f):
		register_name,nbytes=register_id_table[register]
		if register==0x1F:
			nbytes=1
		self.registers[register_name]=read_bytes(f,nbytes)
		return 'REG: %s, VAL: %s' % (register_name,to_hex(self.registers[register_name]))

	def w_register(self,register,f):
		register_name,nbytes=register_id_table[register]
		self.registers[register_name]=read_bytes(f,nbytes)
		return 'REG: %s, VAL: %s' % (register_name,to_hex(self.registers[register_name]))

	def parse_tx(self,p):
		print([hex(x) for x in p])
		r={}
		for k,v in tx_payload_map.items():
			if v['type']=='range':
				int_val=p[v['byte']]
				if False and int_val==v['idle']:
					r[k]='IDLE'
				else:
					r[k]=((float(int_val)-v['min'])/(v['max']-v['min'])-0.5)*200 # return percent
			elif v['type']=='indicator':
				bit=(v['byte']>>v['bit'])&0x01
				r[k]=(bit==1)	
		print(r)
		
xn297=XN297()

while line:
	line=line.decode('utf8').strip()
	time_str,id_str,mosi_str,miso_str = line.split(',')
	mosi_val=int(mosi_str,16)
	additional_str=""
	if 0x00 == (0xE0 & mosi_val):
		command="READ"
		additional_str=str(xn297.r_register(mosi_val & 0x1F , f))	
	elif 0x20 == (0xE0 & mosi_val):
		command="WRITE"
		additional_str=str(xn297.w_register(mosi_val & 0x1F , f))	
	elif 0x61 == mosi_val:
		command="READ RX"
		payload=read_bytes(f,xn297.payload_length)
		cs=compute_checksum_rx(payload,0x6d)
		additional_str="(channel %d) (cs:%s)RX<- %s" % (xn297.channel,hex(cs),to_hex(payload)) 
	elif 0xA0 == mosi_val:
		command="WRITE TX"
		payload=read_bytes(f,xn297.payload_length)
		cs=compute_checksum_tx(payload,0x6d)
		xn297.parse_tx(payload)
		additional_str="(channel %d) (cs:%s)TX-> %s" % (xn297.channel,hex(cs),to_hex(payload)) 
	elif 0xE1 == mosi_val:
		command="FLUSH TX"
		read_bytes(f,1)
	elif 0xE2 == mosi_val:
		command="FLUSH RX"
		read_bytes(f,1)
	elif 0xE3 == mosi_val:
		command="REUSE TX"
	elif 0x50 == mosi_val:
		command="ACT"
	elif 0x60 == mosi_val:
		command="READ RX WIDTH"
	elif 0xA8 == (0xF8 & mosi_val):
		command="W ACK"
	elif 0xB0 == mosi_val:
		command="W TX"
	elif 0xFD == mosi_val:
		command="CE FSPI ON"
		read_bytes(f,1)
	elif 0xFC == mosi_val:
		command="CE FSPI OFF"
		read_bytes(f,1)
	elif 0x53 == mosi_val:
		command="CE FSPI HOLD"
		read_bytes(f,1)
	elif 0xFF == mosi_val:
		command="NOOP"
	elif 0x40 == mosi_val:
		command="UNKNOWN1"
	else:
		print("WHOOPS HAD AN ISSUE",prev_c,"this mosi",hex(mosi_val))
		sys.exit(1)
	if not print_time:
		time_str=""
	print(time_str,command,hex(mosi_val),additional_str)
	prev_c=command	
	line=f.readline()
	
