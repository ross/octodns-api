# octoDNS API - RESTful API for octoDNS

A JSON web service API for interacting with [octoDNS](https://github.com/octodns/octodns/), allowing clients to perform CRUD operations on DNS records.

## Features

- RESTful JSON API for DNS management
- Support for all octoDNS providers (Route53, Cloudflare, etc.)
- API key authentication
- Zone and record operations
- Dry-run sync capabilities

## Installation

### From PyPI

```bash
pip install octodns-api
```

### From source

```bash
git clone https://github.com/octodns/octodns-api.git
cd octodns-api
./script/bootstrap
```

## Configuration

Create an octoDNS configuration file with API key configuration:

```yaml
api:
  keys:
    - name: admin
      key: env/OCTODNS_API_KEY_ADMIN

providers:
  route53:
    class: octodns_route53.Route53Provider
    access_key_id: env/AWS_ACCESS_KEY_ID
    secret_access_key: env/AWS_SECRET_ACCESS_KEY

zones:
  example.com.:
    sources:
      - route53
    targets:
      - route53
```

Set environment variables:

```bash
export OCTODNS_API_KEY_ADMIN=your-secure-random-key-here
export AWS_ACCESS_KEY_ID=your-aws-key
export AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## Running the Server

```bash
octodns-api --config /path/to/config.yaml --host 127.0.0.1 --port 5000
```

Options:
- `--config`: Path to octoDNS configuration file (required)
- `--host`: Host to bind to (default: 127.0.0.1)
- `--port`: Port to bind to (default: 5000)
- `--debug`: Enable debug mode

## API Endpoints

All endpoints require authentication via `Authorization: Bearer <api-key>` header.

### Zones

#### List all zones
```
GET /zones
```

Response:
```json
{
  "zones": ["example.com.", "example.org."]
}
```

#### Get zone details
```
GET /zones/{zone}
```

Response:
```json
{
  "name": "example.com.",
  "decoded_name": "example.com.",
  "records": [
    {
      "name": "www",
      "type": "A",
      "ttl": 300,
      "values": ["1.2.3.4"]
    }
  ]
}
```

#### Sync zone
```
POST /zones/{zone}/sync
Content-Type: application/json

{
  "dry_run": true
}
```

### Records

#### List records in zone
```
GET /zones/{zone}/records
```

#### Get specific record
```
GET /zones/{zone}/records/{name}/{type}
```

Example:
```
GET /zones/example.com./records/www/A
```

Response:
```json
{
  "name": "www",
  "type": "A",
  "ttl": 300,
  "values": ["1.2.3.4"]
}
```

#### Create or update record
```
POST /zones/{zone}/records
Content-Type: application/json

{
  "name": "www",
  "type": "A",
  "ttl": 300,
  "values": ["1.2.3.4"]
}
```

Response:
```json
{
  "record": {
    "name": "www",
    "type": "A",
    "ttl": 300,
    "values": ["1.2.3.4"]
  },
  "changed": true
}
```

#### Delete record
```
DELETE /zones/{zone}/records/{name}/{type}
```

Response:
```json
{
  "deleted": true
}
```

## Authentication

API keys are configured in the config file and can use environment variables:

```yaml
api:
  keys:
    - name: admin
      key: env/OCTODNS_API_KEY_ADMIN
    - name: readonly
      key: env/OCTODNS_API_KEY_READONLY
```

Include the API key in requests:

```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:5000/zones
```

## Development

See the [/script/](/script/) directory for development tools following the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern.

### Setup

```bash
./script/bootstrap
```

### Run tests

```bash
./script/test
```

### Linting

```bash
./script/lint
```

### Formatting

```bash
./script/format
```

## Security Considerations

- Always use HTTPS in production
- Store API keys in environment variables, not in config files
- Use strong, randomly generated API keys (32+ characters)
- Restrict network access to the API server
- Consider placing behind a reverse proxy with rate limiting

## License

MIT License - see LICENSE file for details
