#! /usr/bin/python
from os import environ as env
from keystoneclient.v2_0 import client as ksclient
from neutronclient.v2_0 import client as neutronclient
from prettytable import PrettyTable

import json


keystone = ksclient.Client(auth_url=env['OS_AUTH_URL'],
                           username=env['OS_USERNAME'],
                           password=env['OS_PASSWORD'],
                           tenant_name=env['OS_TENANT_NAME'])
token = keystone.auth_token
nw_endpoint_url = keystone.service_catalog.url_for(service_type='network')
neutron = neutronclient.Client(endpoint_url=nw_endpoint_url, token=token)

"""
  {
    'tenant-id': {
      'network': {
        'subnet' : {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        },
        'network' : {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        },
        'floatingip': {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        },
        'security_group': {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        },
        'router': {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        },
        'port': {
          'usage': <> #insert usage
          'max': <>  #insert quota value
        }
      }
    }
  }
"""

def create_tenant_maps():
  tenant_usage_maps = {}
  tenants = keystone.tenants.list()
  for tenant in tenants:
    tenant_usage_maps[tenant.id] = {}
  return tenant_usage_maps

def insert_network_usage(tenant_usage_maps):

  quota_name_to_list_function = {
    'floatingip': 'list_floatingips',
    'subnet': 'list_subnets',
    'network': 'list_networks',
    'security_group': 'list_security_groups',
    'router': 'list_routers',
    'port': 'list_ports'
  }
  def _each_call_list_api_for_tenant(tenant_usage_maps):

    for tenant_id in tenant_usage_maps:
      network_usage_map = {}
      quotas = neutron.show_quota(tenant_id)['quota']

      for quota_name in quota_name_to_list_function:
        resource_key = quota_name_to_list_function[quota_name].replace('list_','')
        network_usage_map[quota_name] = {}
        network_usage_map[quota_name]['max'] = str(quotas[quota_name])
        network_usage_map[quota_name]['usage'] = str(len(getattr(neutron, quota_name_to_list_function[quota_name])(tenant_id=tenant_id)[resource_key]))
      tenant_usage_maps[tenant_id]['network'] = network_usage_map

  def _call_all_list_and_count(tenant_usage_maps):
    # init maps
    for tenant_id in tenant_usage_maps:
      tenant_usage_maps[tenant_id]['network'] = {}
      quotas = neutron.show_quota(tenant_id)['quota']
      for quota_name in quota_name_to_list_function:
        tenant_usage_maps[tenant_id]['network'][quota_name] = {}
        tenant_usage_maps[tenant_id]['network'][quota_name]['max'] = str(quotas[quota_name])
        tenant_usage_maps[tenant_id]['network'][quota_name]['usage'] = str(0)

    for quota_name in quota_name_to_list_function:
      resource_key = quota_name_to_list_function[quota_name].replace('list_','')
      resources = getattr(neutron, quota_name_to_list_function[quota_name])()[resource_key]
      for rsc in resources:
        if rsc["tenant_id"] in tenant_usage_maps.keys():
          tenant_usage_maps[rsc["tenant_id"]]['network'][quota_name]['usage'] = str(1 + int(tenant_usage_maps[rsc["tenant_id"]]['network'][quota_name]['usage']))
        elif rsc["tenant_id"] is u'':
          # gateway port doesn't have tenant id
          pass
        else:
          print("Not Found tenant: %s for %s(%s)" % (rsc["tenant_id"], quota_name, rsc['id']))

  _call_all_list_and_count(tenant_usage_maps)
  #_each_call_list_api_for_tenant(tenant_usage_maps)




tenant_usage_maps = create_tenant_maps()
insert_network_usage(tenant_usage_maps)

table = PrettyTable(["project", "net", "subnet", "fip", "sg", "router", "port"])
for tenant_id in tenant_usage_maps:
  nw_resource = tenant_usage_maps[tenant_id]["network"]
  table.add_row([tenant_id,
                 nw_resource["network"]["usage"] + "/" + nw_resource["network"]["max"],
                 nw_resource["subnet"]["usage"] + "/" + nw_resource["subnet"]["max"],
                 nw_resource["floatingip"]["usage"] + "/" + nw_resource["floatingip"]["max"],
                 nw_resource["security_group"]["usage"] + "/" + nw_resource["security_group"]["max"],
                 nw_resource["router"]["usage"] + "/" + nw_resource["router"]["max"],
                 nw_resource["port"]["usage"] + "/" + nw_resource["port"]["max"]])

print(table)
