import sys

for line in sys.stdin:
	line=[ int(x,16) for x in line[2:].split('.') ]
	checksum=(sum(line[1:])+0x6d)&0xff
	print(hex(line[0]),hex(checksum),hex(sum(line[1:])),hex(0xff&(line[0]-sum(line[1:]))))
