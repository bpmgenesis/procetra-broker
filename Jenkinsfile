pipeline {
  agent any
  stages {
    stage('whoami') {
      steps {
        sh 'whoami'
      }
    }

    stage('Docker Local Remove') {
      steps {
        sh 'docker rmi apidera/mining-broker:1.0 --force'
      }
    }

    stage('Docker Local Build') {
      steps {
        sh '''docker build -t apidera/mining-broker:1.0 .
'''
      }
    }

    stage('Docker Login') {
      environment {
        DOCKERHUB_USER = 'apidera'
        DOCKERHUB_PASSWORD = 'AAA123bbb'
      }
      steps {
        sh 'docker login -u $DOCKERHUB_USER -p $DOCKERHUB_PASSWORD'
      }
    }

    stage('Docker Push') {
      steps {
        sh 'docker push apidera/mining-broker:1.0'
      }
    }

    stage('Server Publish') {
      steps {
        sh '''whoami &&
eval "$(ssh-agent)" &&
ssh-add ~/.ssh/api_broker &&
ssh root@104.248.197.152 -o StrictHostKeyChecking=no \'cd /brokers && docker-compose down && docker rmi apidera/mining-broker:1.0 -f && docker-compose up --remove-orphans -d\''''
      }
    }

  }
}