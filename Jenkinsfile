pipeline {
    agent any
    
    environment {
        VPS_USER = 'root'             // Utilisateur SSH sur le VPS
        VPS_IP = '212.132.99.71'      // Adresse IP du VPS
        APP_PATH = '/var/www/bls' // Chemin de l'application sur le VPS
        BRANCH = 'main'            // Branche utilisée pour le déploiement
    }

    stages {
    
        stage('Deploy to VPS') {
            steps {
                sshagent(['fortib_server_ssh_key']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP << 'EOF'
                    
                    set -e
                    
                    echo ">>> Déploiement de l'application sur le VPS"

                    # Déployer le backend
                    echo ">>> Mise à jour et redémarrage du backend"
                    cd $APP_PATH
                    echo "Arrete les containers existant..."
                    docker compose down -v --remove-orphans

                    echo "Relancer les containers..."
                    docker compose up --build -d 
        
                    echo ">>> Déploiement terminé avec succès"
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline executed successfully!'
        }
        failure {
            echo 'Pipeline execution failed!'
        }
    }
}
