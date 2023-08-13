import base64
import os.path
import typing
from dataclasses import dataclass
from datetime import datetime

import flask
import yaml
from flask import Flask, render_template

from lib.iso_http import IsoHttpHandler


@dataclass
class HttpHandler:
    prefix: str
    iso_http: IsoHttpHandler
    swf: str
    player_width: int
    player_height: int

    def close(self):
        self.iso_http.close()


app: Flask = Flask(__name__)
_root = ''
_updated: datetime = datetime.now()
_handlers: dict[str, HttpHandler] = {}


def app_unregister():
    for k, v in _handlers.items():
        v.close()


def cfg_load() -> dict:
    with open('config.yaml') as fp:
        config = yaml.safe_load(fp)
    return config


def cfg_create_handler(prefix: str, config: typing.Union[str, dict]) -> HttpHandler:
    if type(config) == str:
        config = {
            'swf': config,
        }

    width = 1024
    height = 768

    player = config.get('player', 'medium')
    if player == 'small':
        width = 800
        height = 600

    return HttpHandler(
        prefix=prefix,
        iso_http=IsoHttpHandler(prefix),
        swf=config['swf'],
        player_width=width,
        player_height=height
    )


def cfg_setup_routes(config: dict) -> str:
    if config['root'] != _root:
        app_unregister()

    for prefix in config['disks']:
        _handlers[prefix] = cfg_create_handler(
            os.path.join(config['root'], prefix),
            config['disks'][prefix]
        )

    return config['root']


@app.route('/-/reload')
def reload():
    global _root
    config = cfg_load()
    _root = cfg_setup_routes(config)
    return 'OK'


@app.route('/')
def get_root():
    return render_template('list.html', paths=_handlers.keys())


@app.route('/<string:prefix>/')
def get_prefix(prefix: str):
    if prefix not in _handlers:
        return flask.Response(status=404)

    handler = _handlers[prefix]

    return render_template('index.html',
                           title=prefix,
                           swf=handler.swf,
                           width=handler.player_width,
                           height=handler.player_height)


@app.route('/<string:prefix>/<path:path>')
def get_prefix_file(prefix: str, path: str):
    if prefix not in _handlers:
        return flask.Response(status=404)

    if not path.startswith('/'):
        path = '/' + path

    handler = _handlers[prefix]
    if not handler.iso_http.exists(path):
        return flask.Response(status=404)

    sz = handler.iso_http.file_sz(path)
    checksum = handler.iso_http.checksum(path)

    headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Length': sz,

        'Cache-Control': 'public, max-age=31536000',
    }
    if checksum is not None:
        headers['Content-Digest'] = 'sha-256=:' + base64.b64encode(checksum).strip().decode('utf-8')

    def generate():
        for chunk in handler.iso_http.read_bytes(path):
            yield chunk

    return generate(), 200, headers


def main():
    global _root
    _root = cfg_setup_routes(cfg_load())
    app.run(host='127.0.0.1', port=8080)


if __name__ == '__main__':
    main()
