[Unit]
Description=bjoern instance NeoAmbi
After=network.target
After=multi-user.target

[Service]
User=sysop
Group=spider
Type=simple
WorkingDirectory=/home/pi/PiClock/Leds/NeoAmbi.py
Environment="PATH=/home/pi/PiClock/Leds/NeoAmbi.py"
ExecStart= sudo /home/pi/PiClock/venv/bin/python3 /home/pi/PiClock/Leds/NeoAmbi.py

[Install]
WantedBy=multi-user.target

