// Azure Front Door Standard + WAF skeleton for ca-market-api / ca-android-api
// RG: rg-zevi-cloudphone only. Do NOT deploy until Day-1 budget confirmed.
// Params are hostnames — look them up with az containerapp show before apply.

@description('Resource group is implied by deployment target')
param location string = 'global'

@description('AFD profile name')
param profileName string = 'afd-zevi-strlix'

@description('Endpoint name')
param endpointName string = 'strlix-edge'

@description('ca-market-api ingress FQDN (no https://)')
param marketOriginHost string

@description('ca-android-api ingress FQDN (no https://)')
param androidOriginHost string

resource profile 'Microsoft.Cdn/profiles@2023-05-01' = {
  name: profileName
  location: location
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
}

resource waf 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2022-05-01' = {
  name: 'wafzevistrlix'
  location: location
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
  properties: {
    policySettings: {
      enabledState: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: 'Enabled'
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'Microsoft_DefaultRuleSet'
          ruleSetVersion: '2.1'
          ruleSetAction: 'Block'
        }
        {
          ruleSetType: 'Microsoft_BotManagerRuleSet'
          ruleSetVersion: '1.0'
        }
      ]
    }
  }
}

resource endpoint 'Microsoft.Cdn/profiles/afdEndpoints@2023-05-01' = {
  parent: profile
  name: endpointName
  location: location
  properties: {
    enabledState: 'Enabled'
  }
}

resource ogMarket 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = {
  parent: profile
  name: 'og-market-api'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/health'
      probeRequestType: 'GET'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 60
    }
  }
}

resource originMarket 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = {
  parent: ogMarket
  name: 'origin-market-api'
  properties: {
    hostName: marketOriginHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: marketOriginHost
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

resource ogAndroid 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = {
  parent: profile
  name: 'og-android-api'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/health'
      probeRequestType: 'GET'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 60
    }
  }
}

resource originAndroid 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = {
  parent: ogAndroid
  name: 'origin-android-api'
  properties: {
    hostName: androidOriginHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: androidOriginHost
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

// Routes are intentionally minimal — refine path patterns after first deploy.
resource routeMarket 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = {
  parent: endpoint
  name: 'route-market'
  dependsOn: [originMarket]
  properties: {
    originGroup: {
      id: ogMarket.id
    }
    supportedProtocols: ['Http', 'Https']
    patternsToMatch: ['/v1/*', '/market/*', '/health', '/ready', '/docs', '/openapi.json']
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    httpsRedirect: 'Enabled'
  }
}

resource routeAndroid 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = {
  parent: endpoint
  name: 'route-android'
  dependsOn: [originAndroid]
  properties: {
    originGroup: {
      id: ogAndroid.id
    }
    supportedProtocols: ['Http', 'Https']
    patternsToMatch: ['/android/*', '/agent/*']
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    httpsRedirect: 'Enabled'
  }
}

output afdEndpointHost string = endpoint.properties.hostName
output wafPolicyId string = waf.id
