// Existing phonecodex-dev only. Does not create OpenAI or open NSGs.
// Secrets stay in App Service settings, not here.

param location string = 'westus3'
param appName string = 'phonecodex-backend'
param planName string = 'phonecodex-backend-plan'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  sku: {
    name: 'P1v3'
    tier: 'PremiumV3'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource web 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    reserved: true
    siteConfig: {
      linuxFxVersion: 'NODE|20-lts'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appCommandLine: 'node server.js'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'STRLIX_REQUIRE_APP_SECRET'
          value: '1'
        }
      ]
    }
  }
}

output defaultHostName string = web.properties.defaultHostName
