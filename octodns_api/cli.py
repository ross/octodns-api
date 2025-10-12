#!/usr/bin/env python
#
#
#

from octodns.cmds.args import ArgumentParser

from octodns_api.app import create_app


def main():
    parser = ArgumentParser(description='Run octoDNS API server')
    parser.add_argument(
        '--config-file',
        required=True,
        help='Path to octoDNS configuration file',
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)',
    )
    parser.add_argument(
        '--port', type=int, default=5000, help='Port to bind to (default: 5000)'
    )

    args = parser.parse_args()

    app = create_app(args.config_file)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
