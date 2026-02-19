# APT Package Installation Guide

## Quick Installation (Debian/Ubuntu)

### Method 1: Install from .deb package

```bash
# Download the package (or build it yourself)
sudo dpkg -i dataset-viz_1.0.0_all.deb

# If dependencies are missing, run:
sudo apt-get install -f
```

That's it! The service will start automatically.

**Access the application:** http://localhost:8081

---

## Building the Package

If you want to build the package yourself:

```bash
# Make the build script executable
chmod +x build-deb.sh

# Build the package
./build-deb.sh
```

This creates `releases/dataset-viz_1.0.0_all.deb`

---

## Using the Application

### Command Line Interface

After installation, use the `dataset-viz` command:

```bash
# Start the service
dataset-viz start

# Stop the service
dataset-viz stop

# Restart the service
dataset-viz restart

# Check status
dataset-viz status

# View logs
dataset-viz logs

# Open in browser
dataset-viz open
```

### Systemd Service

The application runs as a systemd service:

```bash
# Start
sudo systemctl start dataset-viz

# Stop
sudo systemctl stop dataset-viz

# Enable on boot
sudo systemctl enable dataset-viz

# Disable on boot
sudo systemctl disable dataset-viz

# Check status
sudo systemctl status dataset-viz

# View logs
sudo journalctl -u dataset-viz -f
```

---

## Uninstallation

### Remove the package

```bash
# Remove package (keeps config files)
sudo apt remove dataset-viz

# Remove package and config files
sudo apt purge dataset-viz
```

---

## Package Details

**Package Name:** dataset-viz  
**Version:** 1.0.0  
**Architecture:** all  
**Dependencies:** python3 (>= 3.8), python3-pip

**Installed Files:**
- Application: `/opt/dataset-viz/`
- Service: `/etc/systemd/system/dataset-viz.service`
- CLI: `/usr/local/bin/dataset-viz`
- Desktop Entry: `/usr/share/applications/dataset-viz.desktop`

**Port:** 8081  
**URL:** http://localhost:8081

---

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u dataset-viz -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8081

# Manually test
cd /opt/dataset-viz
python3 app.py
```

### Dependencies missing

```bash
# Reinstall dependencies
cd /opt/dataset-viz
sudo pip3 install -r requirements.txt
```

### Permission issues

```bash
# Fix permissions
sudo chown -R root:root /opt/dataset-viz
sudo chmod -R 755 /opt/dataset-viz
```

---

## Features

✅ **Multi-GB Dataset Support** - Handle files up to 5GB  
✅ **Modern UI** - Dark mode with glassmorphism  
✅ **Multiple Export Formats** - CSV, Excel, JSON, Parquet  
✅ **Correlation Analysis** - Numeric relationship detection  
✅ **Advanced Preprocessing** - Normalize, standardize, encode, outlier handling  
✅ **HTML Reports** - Comprehensive analysis reports  
✅ **Auto-start on Boot** - Systemd service integration  

---

## Support

For issues or questions:
- Check logs: `dataset-viz logs`
- View status: `dataset-viz status`
- GitHub: [Your repository URL]
