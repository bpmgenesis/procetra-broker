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

  }
}