import sys
import bisect

if len(sys.argv)!=4:
	print(sys.argv[0],"time[0/1] mosi.csv spi_enable.csv")
	sys.exit(1)

print_time=int(sys.argv[1])==1
fn_mosi=sys.argv[2]
fn_spienable=sys.argv[3]

spi_enable=[]
f_spienable=open(fn_spienable,'r')
f_spienable.readline()
for line in f_spienable:
	time_str,spi_enable_state=line.split(',')
	spi_enable.append((float(time_str),spi_enable_state))

f=open(fn_mosi,'r')
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
	

def read_bytes(f,n,timeout=0.0001):
	bytes_=[]
	prev_time=-1
	while n>0:
		prev_pos=f.tell()
		line=f.readline()
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

			
			
		

xn297=XN297()

while line:
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
		additional_str="(channel %d) RX<- %s" % (xn297.channel,to_hex(payload)) 
	elif 0xA0 == mosi_val:
		command="WRITE TX"
		payload=read_bytes(f,xn297.payload_length)
		additional_str="(channel %d) TX-> %s" % (xn297.channel,to_hex(payload)) 
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
	
