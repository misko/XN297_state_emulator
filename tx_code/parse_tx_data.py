import functools
import sys
hit_a=0
hit_b=0
total=0
for line in sys.stdin:
	line=[ int(x,16) for x in line[2:].split('.') ]
	checksum_a=(sum(line[1:])+0xab)&0xff
	if checksum_a==line[0]:
		hit_a+=1
	checksum_b=functools.reduce(lambda a,b : a ^ b , line[1:]+[0x6d])
	if checksum_b==line[0]:
		hit_b+=1

	total+=1
	print(hex(line[0]),hex(checksum_a),hex(checksum_b),hex(sum(line[1:])),hex(0xff&(line[0]-sum(line[1:]))))
print(hit_a,hit_b,total)
