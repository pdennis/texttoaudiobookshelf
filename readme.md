# Text to Audiobookshelf

A Flask web application that converts text to speech using Kokoro TTS and automatically uploads the resulting audio files to an Audiobookshelf server. Features a modern, responsive UI with real-time processing status updates.
!./t2abs.png
## Features

- Convert text to natural-sounding speech using Kokoro TTS
- Multiple voice options (US/UK, male/female)
- Automatic splitting of long texts into manageable chunks
- Direct upload to Audiobookshelf server
- Real-time processing status updates
- Configuration management through web interface
- Systemd service integration for 24/7 availability

## Prerequisites

- Python 3.8+
- Audiobookshelf server instance
- Linux system with systemd (for service deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pdennis/texttoaudiobookshelf
cd texttoaudiobookshelf
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Configure Audiobookshelf settings:
- Get your Audiobookshelf server URL
- Generate an API token from your Audiobookshelf instance
- Update `config.json` with your settings or use the web interface

## Development Setup

Run the Flask development server:
```bash
python app.py
```

The application will be available at `http://localhost:10108`

## Production Deployment for Homelab

1. Create the Gunicorn configuration file (`gunicorn_config.py`):
```python
workers = 2
bind = '0.0.0.0:10108'
timeout = 120
worker_class = 'sync'
accesslog = '/var/log/textlistens/access.log'
errorlog = '/var/log/textlistens/error.log'
capture_output = True
```

2. Create systemd service file (`/etc/systemd/system/textlistens.service`):
```ini
[Unit]
Description=TextListens Gunicorn Service
After=network.target

[Service]
User=your_username
Group=your_username
WorkingDirectory=/path/to/texttoaudiobookshelf
Environment="PATH=/path/to/texttoaudiobookshelf/venv/bin"
ExecStart=/path/to/texttoaudiobookshelf/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
```

3. Create log directory:
```bash
sudo mkdir -p /var/log/textlistens
sudo chown your_username:your_username /var/log/textlistens
```

4. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable textlistens
sudo systemctl start textlistens
```

## Usage

1. Access the web interface at `http://your_server:10108`
2. Configure your Audiobookshelf connection (first time only):
   - Click "Show Settings"
   - Enter your Audiobookshelf URL and API token
   - Click "Save Configuration"
3. Convert text to audio:
   - Enter a title for your audiobook
   - Select a voice
   - Paste or type your text content
   - Click "Convert to Audio"
4. Monitor the progress bar for conversion status
5. Click the provided link to access your audiobook in Audiobookshelf

## Monitoring and Logs

View service status:
```bash
sudo systemctl status textlistens
```

Monitor logs:
```bash
# Service logs
sudo journalctl -u textlistens -f

# Access logs
tail -f /var/log/textlistens/access.log

# Error logs
tail -f /var/log/textlistens/error.log
```

## Configuration

The application uses a `config.json` file for storing settings:
```json
{
    "AUDIOBOOKSHELF_URL": "http://your_server:13378",
    "AUDIOBOOKSHELF_TOKEN": "your_api_token"
}
```

Settings can be updated either by:
- Editing `config.json` directly
- Using the web interface configuration panel

## Troubleshooting

1. Service won't start:
   - Check logs: `sudo journalctl -u textlistens -f`
   - Verify paths in systemd service file
   - Ensure proper permissions on log directory

2. Upload fails:
   - Verify Audiobookshelf URL and token
   - Check network connectivity
   - Review error logs

3. Audio generation issues:
   - Ensure enough disk space
   - Verify GPU availability if configured
   - Check text length and formatting


