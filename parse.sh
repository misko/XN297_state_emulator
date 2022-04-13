for d in data/*; do
	echo $d
	python3 parse_csv.py 0 $d/mosi.csv.gz $d/spienable.csv.gz > $d/xn297_state      
	grep "RX\|TX" $d/xn297_state | sort | uniq -c > $d/all_RXTX
	grep "RX" $d/xn297_state | sort | uniq -c > $d/all_RX
	grep "TX" $d/xn297_state | sort | uniq -c > $d/all_TX
done

#python3 parse_csv.py 0 remote_with_drone_already_on_10s/mosi.csv remote_with_drone_already_on_10s/spi_enable.csv > remote_with_drone_already_on_10s/xns297_state
#python3 parse_csv.py 0 remote_alone_10s_repeat/mosi.csv remote_alone_10s_repeat/spienable.csv > remote_alone_10s_repeat/xn297_state
#python3 parse_csv.py 0 remote_alone_gps_switched_10s/mosi.csv remote_alone_gps_switched_10s/spienable.csv > remote_alone_gps_switched_10s/xn297_state
