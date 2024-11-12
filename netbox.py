import pynetbox
import requests
import ipaddress
from config import config

session = requests.Session()
session.verify = False
netbox = pynetbox.api(config['netbox']['url'], token=config['netbox']['api_token'])
netbox.http_session = session

print(f"Netbox URL: {config['netbox']['url']}")

def check_device_exists(serial_number):
  if netbox.dcim.devices.count(serial=serial_number) == 0:
    return False
  return True

def create_device(serial_number, installed_image, model_number):
  image = installed_image.split('/')[1]
  device_type = netbox.dcim.device_types.get(part_number=model_number)
  status = 'planned'

  if image != device_type.custom_fields['latest_image']:
    status = 'image_needed'

  device = netbox.dcim.devices.create(
    name=serial_number,
    site=netbox.dcim.sites.get(name="Provisjonering").id,
    role=netbox.dcim.device_roles.get(name='Access Switch').id,
    device_type=device_type.id,
    serial=serial_number,
    status=status,
    custom_fields={
      "installed_image": image
    }
  )

  return device

def update_device(serial_number, installed_image):
  image = installed_image.split('/')[1]
  device = get_device(serial_number)
  device_type = get_device_type(device.device_type.model)

  if image != device_type.custom_fields['latest_image']:
    return

  return device.update({
    "status": 'planned',
    "custom_fields": {
      "installed_image": image
    }
  })

def get_devices():
  return list(netbox.dcim.devices.all())

def get_device(serial_number):
  return netbox.dcim.devices.get(serial=serial_number)

def get_device_type(model_number):
  return netbox.dcim.device_types.get(part_number=model_number)

def render_config(serial_number):
  device = get_device(serial_number)
  
  headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {config['netbox']['api_token']}"
  }

  response = requests.post(f"{config['netbox']['url']}/api/dcim/devices/{device.id}/render-config/", headers=headers, verify=False)

  return response.json()['content']

def update_status(serial_number, status):
  device = get_device(serial_number)
 
  device.update({
    "status": status
  })

  return device