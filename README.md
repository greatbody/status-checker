# Status Monitor

This is a simple web application to monitor the status of websites. It checks the status of configured websites every 5 minutes and displays the results in a dashboard.

## Features
- Monitor multiple websites
- Dashboard displaying the status of each website
- Edit configuration for monitored websites
- Status history stored in SQLite
- Dockerized for easy deployment

## Getting Started

### Prerequisites
- Docker

### Running the Application
1. Clone the repository.
2. Navigate to the project directory.
3. Build the Docker image:
   ```bash
   docker build -t status_monitor .
   ```
4. Run the Docker container, mounting the data directory:
   ```bash
   docker run -d -p 5000:5000 -v /path/to/data:/app/data status_monitor
   ```
5. Access the application at `http://localhost:5000`.

## License
This project is licensed under the MIT License.
