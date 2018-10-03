from __future__ import print_function

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import logging
import os
import re
import json
from datetime import datetime

import mimetypes
from flask import request, Response, render_template
from flask import Flask

LOG = logging.getLogger(__name__)
app = Flask(__name__)

MOVIE_PATH = "/home/media/mnt"
LOG_PATH = "/home/logs/stream.log"
MB = 1 << 20
BUFF_SIZE = 10 * MB


@app.route('/<string:movie_url>')
def home(movie_url):
    LOG.info("REQUEST @ DT {} @ HEADERS {}".format(datetime.now(), request.headers))
    response = render_template(
        'index.html',
        time=str(datetime.now()),
        movie='/stream/{}'.format(movie_url),
    )
    return response


@app.route('/structure')
def structure():
    return Response(
        json.dumps({
            key.replace(MOVIE_PATH, ""): value
            for key, _, value in os.walk(MOVIE_PATH + '/')
        }),
        status=200,
        content_type='application/json'
    )


def partial_response(path, start, end=None):
    try:
        file_size = os.path.getsize(path)
    except:
        return Response(
            "not such file",
            400
        )

    # Determine (end, length)
    if end is None:
        end = start + BUFF_SIZE - 1
    end = min(end, file_size - 1)
    end = min(end, start + BUFF_SIZE - 1)
    length = end - start + 1

    # Read file
    with open(path, 'rb') as fd:
        fd.seek(start)
        bytes = fd.read(length)
    assert len(bytes) == length

    response = Response(
        bytes,
        206,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True,
    )
    response.headers.add(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'
    )
    return response


def get_range(req):
    range_x = req.headers.get('Range', None)
    if not range_x:
        return 0, None

    m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range_x)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None


@app.route('/stream/<string:movie_name>')
def stream_movie(movie_name):
    path = '{movie_path}/{movie_name}'.format(movie_path=MOVIE_PATH, movie_name=movie_name)

    start, end = get_range(request)
    return partial_response(path, start, end)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    HOST = '0.0.0.0'
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8080)
    IOLoop.instance().start()

    # Standalone
    # app.run(host=HOST, port=5000, debug=True)

