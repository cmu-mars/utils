#/bin/bash
docker pull cmumars/p2-cp3
for i in testcase*; do
  echo "Running " $i
  cd $i
  chmod -R 0777 logs roslogs
  python run-test.py > TH_LOG
  docker system prune -f
  cd ..
done