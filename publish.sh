docker rmi apidera/mining-broker:1.0
docker build -t apidera/mining-broker:1.0 .
docker push apidera/mining-broker:1.0
ssh root@104.248.197.152 'cd /brokers && docker-compose down && docker rmi apidera/mining-broker:1.0 -f && docker-compose up --remove-orphans -d'