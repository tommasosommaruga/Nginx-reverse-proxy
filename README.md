# Nginx Reverse Proxy for NextJS Web Application

This project demonstrates the implementation of Nginx as a reverse proxy for a NextJS web application, focusing on enhanced security and performance optimization.

## Project Structure

```
Nginx-reverse-proxy_sommaruga/
├── README.md
└── ... (configuration files)

nextjs-webapp/ (Not included in repository due to size)
├── ... (NextJS application files in Docker container)

dashboard/ 
├── ... (Python-based dashboard files)
```

> **Note:** The NextJS webapp is referenced in this documentation but not included in the repository due to its size.

## Overview

This setup uses Nginx as a reverse proxy to forward client requests to a containerized NextJS backend application and a Python dashboard. Key architectural points:

- NextJS webapp runs in Docker containers
- Dashboard implemented using Python
- Nginx runs directly on the host machine (outside Docker)
- This architecture avoids Docker network forwarding constraints

## Setup Instructions

### Prerequisites

- Docker and Docker Compose (for containerized webapp)
- Nginx (installed on host machine)
- Python (for dashboard)
- Node.js and npm (for local development)

### Configuration

1. Clone this repository
2. Initialize the NextJS webapp using Docker:
    ```bash
    cd nextjs-webapp
    docker-compose up -d
    ```
3. Set up the Python dashboard
4. Configure Nginx on the host machine using the provided configuration files
5. Start the services

## Usage

### Starting the Services

```bash
# Start Nginx reverse proxy on host
sudo systemctl start nginx

# The NextJS application is already running in Docker containers
# Start the Python dashboard if needed
cd dashboard
python app.py
```

### Testing the Setup

Access the application through the Nginx proxy:
```
http://localhost
```

## Security Considerations

- All traffic is routed through Nginx, hiding the actual application server
- HTTP headers are sanitized to prevent information disclosure
- Rate limiting is implemented to prevent DoS attacks
- HTTPS can be configured for encrypted communication
- Direct Nginx implementation avoids Docker network security concerns

## References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [NextJS Documentation](https://nextjs.org/docs)
- [Web Application Security Best Practices](https://owasp.org/www-project-web-security-testing-guide/)
- [Docker Documentation](https://docs.docker.com/)