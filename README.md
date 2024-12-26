# TubR

docker-compose -f docker-compose.yml -p tubr-container up

gcloud builds submit --tag gcr.io/sincere-axon-434017-j2/r1
gcloud run deploy --image gcr.io/sincere-axon-434017-j2/r1 --platform managed --memory 4Gi

gcloud beta run domain-mappings create --service r1 --domain trubr.net
