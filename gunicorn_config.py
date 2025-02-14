# gunicorn_config.py
workers = 2
bind = '0.0.0.0:10108'
timeout = 120
worker_class = 'sync'
accesslog = '/var/log/textlistens/access.log'
errorlog = '/var/log/textlistens/error.log'
capture_output = True
