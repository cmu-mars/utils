#!/bin/bash
for i in testcase*; do
	logs=$(realpath .)
	docker run -v $logs/$i/logs:/home/mars/logs -v $logs/$i/params:/home/mars/params -p 1045:1044 -it cmumars/cp3_rb_icse
done