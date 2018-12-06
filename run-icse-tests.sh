#!/bin/bash
total=$(ls | wc -l)
total=$(( total - 1 ))
done=1
startdate=$SECONDS
for i in testcase*; do
	logs=$(realpath .)
	if [ -f $logs/$i/logs/plan ]; then
	  done=$(( done+1 ))
	  continue;
	fi
	enddate=$SECONDS
	echo "Doing run $done/$total: $logs/$i"
	date -u -d "0 $enddate seconds - $startdate seconds" +"%H:%M:%S"
	done=$(( done+1 ))
	docker run -v $logs/$i/logs:/home/mars/logs -v $logs/$i/params:/home/mars/params -p 1045:1044 -it cmumars/cp3_rb_icse > $logs/$i/docker.out
done

