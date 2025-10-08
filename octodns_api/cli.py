#!/usr/bin/env python
#
#
#

from argparse import ArgumentParser

from .app import create_app


def main():
    parser = ArgumentParser(description='Run octoDNS API server')
    parser.add_argument(
        '--config', required=True, help='Path to octoDNS configuration file'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)',
    )
    parser.add_argument(
        '--port', type=int, default=5000, help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug', action='store_true', help='Enable debug mode'
    )

    args = parser.parse_args()

    app = create_app(args.config)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
