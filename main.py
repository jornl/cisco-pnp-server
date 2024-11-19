import re
from pprint import pprint
import xmltodict
from flask import Flask, request, send_from_directory, render_template, Response
from config import config

from netbox import check_device_exists, create_device, get_device_type, update_device, update_status, get_device, render_config

app = Flask(__name__, template_folder='templates')

DEVICE_UDI = re.compile(r'PID:(?P<product_id>\w+(?:-\w+)*),VID:(?P<hw_version>\w+),SN:(?P<serial_number>\w+)')


def pnp_device_info(udi, correlator):
    return render_template("device_info.xml", **{
        "udi": udi,
        "correlator_id": correlator,
    })

def pnp_backoff(udi: str, correlator: str, minutes: int =  1) -> str:
    return render_template("backoff.xml", **{
        "udi": udi,
        "correlator_id": correlator,
        "minutes": int(minutes)
    })

def pnp_install_image(udi, correlator, image_filename, image_checksum=None):
    return render_template("image_install.xml", **{
        "udi": udi,
        "correlator_id": correlator,
        "pnp_server": config['pnp']['host'],
        "image_filename": image_filename,
        "image_checksum": image_checksum
    })

def pnp_bye(udi, correlator):
    return render_template("bye.xml", **{
        "udi": udi,
        "correlator_id": correlator
    })

@app.route('/config/<serial_number>')
def serve_config(serial_number: str):
    return Response(render_config(serial_number), mimetype='text/plain')

@app.route('/images/<path:path>')
def serve_image(path):
    return send_from_directory("images", path)

@app.route('/pnp/HELLO')
def pnp_hello():
    return '', 200

@app.route('/pnp/WORK-REQUEST', methods=['POST'])
def pnp_work_request():
    print("---- WORK REQUEST ----")
    data = xmltodict.parse(request.data)
    print(data)
    print("---- /WORK REQUEST ----")

    udi, correlator_id = data['pnp']['@udi'], data['pnp']['info']['@correlator']
    
    udi_match = DEVICE_UDI.match(udi)
    serial_number = udi_match.group('serial_number')

    if not check_device_exists(serial_number):
        return Response(pnp_device_info(udi, correlator_id), mimetype='application/xml')
    
    device = get_device(serial_number)

    if device.status.value == 'planned':
        print(f"Device {device} is planned")
        return Response(pnp_backoff(udi, correlator_id, 5), mimetype='application/xml')
    
    if device.status.value == 'image_needed':
        print(f"Device {device} needs image")
        device_type = get_device_type(device.device_type.model)
        image_filename = device_type.custom_fields['latest_image']
        image_checksum = device_type.custom_fields['latest_image_checksum']

        return Response(pnp_install_image(udi, correlator_id, image_filename, image_checksum), mimetype='application/xml')
    
    if device.status.value == 'image_updated':
        print(f"Device {device} has updated image")
        return Response(pnp_device_info(udi, correlator_id), mimetype='application/xml')
    

    if device.status.value == 'staged':
        # Device is staged, we can proceed with the configuration
        print(f"Device {device} is staged")

        location = f"{config['pnp']['host']}/config/{device.serial}"

        return Response(render_template('load_config.xml', {
            "udi": udi,
            "correlator_id": correlator_id,
            "location": location
        }), mimetype='application/xml')

    return Response(render_template('backoff.xml', **{
        "udi": udi,
        "correlator_id": correlator_id,
        "minutes": 5
    }))


@app.route('/pnp/WORK-RESPONSE', methods=['POST'])
def pnp_work_response():
    print("---- WORK RESPONSE ----")
    data = xmltodict.parse(request.data)
    print(data)
    print("---- /WORK RESPONSE ----")
    udi = data['pnp']['@udi']
    correlator_id = data['pnp']['response']['@correlator']
        
    udi_match = DEVICE_UDI.match(udi)
    serial_number = udi_match.group('serial_number')

    job_type = data['pnp']['response']['@xmlns']
    job_status = int(data['pnp']['response']['@success'])

    if job_type == 'urn:cisco:pnp:device-info':
        if job_status == 1:
            device_info = data['pnp']['response']['hardwareInfo']
            image_info = data['pnp']['response']['imageInfo']
            if not check_device_exists(device_info['boardId']):
                create_device(device_info['boardId'], image_info['imageFile'], image_info['versionString'], device_info['platformName'])
            else:
                update_device(device_info['boardId'], image_info['imageFile'], image_info['versionString'])
            return Response(pnp_bye(udi, correlator_id), mimetype='application/xml')
        
    if job_type == 'urn:cisco:pnp:image-install':
        if job_status == 1:
            print("Image install job successful")
            update_status(serial_number, 'image_updated')
            return Response(pnp_device_info(udi, correlator_id), mimetype='application/xml')

    if job_type == 'urn:cisco:pnp:config-upgrade':
        if job_status == 1:
            device_info = data['pnp']['response']['hardwareInfo']
            update_status(device_info['boardId'], 'provisioned')
            print("Configuration job successful")
        print(data)

    return Response(pnp_bye(udi, correlator_id), mimetype='application/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)