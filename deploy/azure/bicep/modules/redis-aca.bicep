// Redis foundation via Container Apps (Azure Cache for Redis *create* blocked — product retiring).
// Phase-2: Azure Managed Redis / Enterprise with Private Endpoint + VNet-integrated CAE.
param name string
param location string
param environmentId string
param tags object = {}
@secure()
param redisPassword string

resource ca 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 6379
        exposedPort: 6380
        transport: 'tcp'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'redis'
          image: 'redis:7-alpine'
          args: [
            'redis-server'
            '--bind'
            '0.0.0.0'
            '--requirepass'
            redisPassword
            '--appendonly'
            'yes'
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Readiness'
              tcpSocket: { port: 6379 }
              initialDelaySeconds: 3
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = ca.properties.configuration.ingress.fqdn
output note string = 'ACA Redis is credit-safe foundation; upgrade to Managed Redis for PE/SLA at scale.'
