# Generate map data:

On an amazon instance:
```
> mkdir data; chmod 777 data
> docker run -v /home/brassdev/data/:/usr/src/app/data -it cmumars/p2-cp3
```
This runs a docker image, and setting up data to be put on the host instance at /home/brassdev/data. To collect map data, inside the docker image do:

```
> . entrypoint.sh ; cd /usr/src/app
> ./gather-data.sh data/data-machineX.csv
```
This runs the robot on all segments in all configurations, at all speeds. This runs in an infinite loop, but it takes a long time (i.e., several days) to run through the loop once.

Copy to local machine and put concat into <ALL.csv>, and then:
```
> python3 map-data-producer.py  -i -m ../../catkin_ws/src/cp3_base/maps/cp3.json <ALL.csv> 
```
This produces the map data for success rate and hit rate and time on the map for all the configurations in ALL.csv.


# Generate instruction data:

```
. entrypoint.sh ; cd /usr/src/app

for i in {0..14}; do sshpass -p 'PASSWD' ssh brassdev@${machines[$i]} << EOF
x=\$(ls instructions/ | grep -v '^l5*.*$')
mkdir \$x ; cp instructions/* \$x/; tar zcf i-rc3-\$x.tgz \$x/
EOF
            donefor i in {0..14}; do

amcl-kinect, mrpt-lidar, aruco, amcl-lidar, mrpt-kinect
```
To join all the instructions, do
```
python join-instructions.py -o instructions-all.json -c favor-efficiency-amcl-kinect ../run-data/efficiency-amcl-kinect/ -c favor-efficiency-amcl-lidar ../run-data/efficiency-amcl-lidar/ -c favor-efficiency-aruco-camera ../run-data/efficiency-aruco/ -c favor-efficiency-mrpt-kinect ../run-data/efficiency-mrpt-kinect/ -c favor-efficiency-mrpt-lidar ../run-data/efficiency-mrpt-lidar/ -c favor-safety-amcl-kinect ../run-data/safety-amcl-kinect/ -c favor-safety-amcl-lidar ../run-data/safety-amcl-lidar/ -c favor-safety-aruco-camera ../run-data/safety-aruco/ -c favor-safety-mrpt-kinect ../run-data/safety-mrpt-kinect/ -c favor-safety-mrpt-lidar ../run-data/safety-mrpt-lidar/ -c favor-timeliness-amcl-kinect ../run-data/timeliness-amcl-kinect/ -c favor-timeliness-amcl-lidar ../run-data/timeliness-amcl-lidar/ -c favor-timeliness-aruco-camera ../run-data/timeliness-aruco/ -c favor-timeliness-mrpt-kinect ../run-data/timeliness-mrpt-kinect/ -c favor-timeliness-mrpt-lidar ../run-data/timeliness-mrpt-lidar/ 58
```

# Run test cases:

## Generate test cases
For example, to generate 29 test cases for 15 machines to run, do:

```
> python3 test-case-generator.py -e -m 15 29
> for i in machine*; do tar zcf $i.tgz $i; done
```

## Copy to the different machines
```
> for i in {0..14}; do
  sshpass -p 'PASSWD' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null machine$i.tgz brassdev@${machines[$i]}:
  sshpass -p 'PASSWD' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null brassdev@${machines[$i]} << EOF
    tar zxf machine$i.tgz
    cd machine$i
    chmod +x run-all-tests.sh
    for t in testcase-*; do chmod -R 777 \$t/logs \$t/roslogs ; done 
EOF
done
```
Then, on each instance do:
```
> cd machine<I>
> ./run-all-tests.sh
```

Copy test cases to local machine:

```
> for i in {0..14}; do sshpass -p 'PASSWD' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null brassdev@${machines[$i]} tar zcf machine${i}-results.tgz machine${i}; sshpass -p 'PASSWD' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null brassdev@${machines[$i]}:machine${i}-results.tgz .; done
```

Process test cass

In cp3/ta
```sh
# Copy all the results into one directory
> for i in {0..14}; do tar zxf machine${i}-results.tgz; done
> mv machine[0-9]/* .
> mv machine[0-9][0-9]/* .
# Process the data into csv files
> for c in {a,b,c}; do for i in ../../../testing-results/RC2/*-${c}; do python process-data.py ../../../testing-results/RC2/data-${c}.csv $i; done; done
```
In the dicrectory containing data-*.csv:

```
> python ../../utils/clean-data.py
```
