
# test bitbucket webhook
curl -X POST -H "User-Agent: Bitbucket-Webhooks/2.0" -H "X-Request-UUID: d0fe7a78-8f44-4ce1-9af3-5af731113caa" -H "X-Event-Key: repo:push" -H "X-Attempt-Number: 1" -H "X-Hook-UUID: 0ae064cd-be16-4e85-9824-3fc68f967d16" -H "Content-Type: application/json" -d@bitbucket.json 'http://localhost:8001'
