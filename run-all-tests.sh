#/bin/bash
docker pull cmumars/p2-cp3

total=$(ls -l testcase* | wc -l)
run=1
for i in testcase*; do
  echo "$run/$total: Running " $i
  run=$(( run + 1 ))
  cd $i
  chmod -R 0777 logs roslogs
  python run-test.py > TH_LOG
  docker system prune -f
  cd ..
done