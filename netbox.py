import pynetbox
import requests
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

def create_device(serial_number, hardware_info, image_info):
  if "/" in image_info['imageFile']:
    image = image_info['imageFile'].split('/')[1]
  else:
    image = image_info['imageFile'].split(':')[1]

  device_type = netbox.dcim.device_types.get(part_number=hardware_info['platformName'])
 
  device = netbox.dcim.devices.create(
    name=hardware_info['hostname'] if hardware_info['hostname'] != "Switch" else serial_number,
    site=netbox.dcim.sites.get(name=config['netbox']['default_site']).id,
    role=netbox.dcim.device_roles.get(name=config['netbox']['default_role']).id,
    device_type=device_type.id,
    serial=serial_number,
    status='planned',
    custom_fields={
      "installed_image": image,
      "installed_image_version": image_info['versionString']
    }
  )

  if image_info['versionString'] != device_type.custom_fields['latest_image_version']:
    add_device_tag(serial_number, "image-needed")

  return device

def update_device(serial_number, hardware_info, image_info):
  if "/" in image_info['imageFile']:
    image = image_info['imageFile'].split('/')[1]
  else:
    image = image_info['imageFile'].split(':')[1]

  device = get_device(serial_number)

  return device.update({
    "name": hardware_info['hostname'] if hardware_info['hostname'] != "Switch" else serial_number,
    "custom_fields": {
      "installed_image": image,
      "installed_image_version": image_info['versionString']
    }
  })

def get_devices():
  return list(netbox.dcim.devices.all())

def add_device_tag(serial_number, slug):
  device = get_device(serial_number)
  device.tags.append({"slug": slug})
  return device.save()

def remove_device_tag(serial_number, slug):
  device = get_device(serial_number)
  tag_exists = next((tag for tag in device.tags if tag.slug == slug), None)
  if tag_exists:
    device.tags.remove(tag_exists)
    return device.save()
  return None

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