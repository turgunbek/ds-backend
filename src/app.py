import logging
import requests
from flask import Flask, request
from models.plate_reader import PlateReader, InvalidImage
from image_provider_client import ImageProviderClient
import io


IMGS_IDX = set([10022, 9965])
IMGS_HOST = 'http://178.154.220.122:7777'

app = Flask(__name__)

plate_reader = PlateReader.load_from_file(
    path='./model_weights/plate_reader_model.pth'
)

provider_client = ImageProviderClient(IMGS_HOST)


# <url>:8080/readPlateNumber?image_ids=<image_id1,image_id2,...>
# {"9965": "о101но750"}
@app.route('/readPlateNumber')
def read_plate_number():
    if 'image_ids' not in request.args:
        return {'error': 'field "image_ids" is not specified'}, 400

    image_ids = request.args['image_ids'].split(',')

    answers = {}

    for image_id in image_ids:
        try:
            image_id = int(image_id)
        except ValueError:
            return {'error': f'image id must be integer: {image_id}'}, 400

        if image_id not in IMGS_IDX:
            return {'error': f'image id not found: {image_id}'}, 404

        try:
            image = provider_client.get_image(image_id)
        except requests.exceptions.Timeout:
            return {'error': 'timeout for accessing the server with images '
                    'has been reached'}, 504
        except Exception:
            return {'error': 'error accessing the server with images'}, 500

        try:
            image = io.BytesIO(image)
        except TypeError:
            return {'error': 'the server with images should return jpeg in '
                    'binary form'}, 500

        try:
            res = plate_reader.read_text(image)
        except InvalidImage:
            logging.error('invalid image')
            return {'error': 'invalid image'}, 400

        answers[image_id] = res

    return answers


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(levelname)s] [%(asctime)s] %(message)s',
        level=logging.INFO,
    )

    app.config['JSON_AS_ASCII'] = False
    app.run(host='0.0.0.0', port=8080, debug=True)
