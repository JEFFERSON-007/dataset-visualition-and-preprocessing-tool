# APT Package Installation Guide

## Quick Installation (Debian/Ubuntu)

### Method 1: Install from .deb package

```bash
# Download the package (or build it yourself)
sudo dpkg -i datalyze_1.0.0_all.deb

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

This creates `releases/datalyze_1.0.0_all.deb`

---

## Using the Application

### Command Line Interface

After installation, use the `datalyze` command:

```bash
# Start the service
datalyze start

# Stop the service
datalyze stop

# Restart the service
datalyze restart

# Check status
datalyze status

# View logs
datalyze logs

# Open in browser
datalyze open
```

### Systemd Service

The application runs as a systemd service:

```bash
# Start
sudo systemctl start datalyze

# Stop
sudo systemctl stop datalyze

# Enable on boot
sudo systemctl enable datalyze

# Disable on boot
sudo systemctl disable datalyze

# Check status
sudo systemctl status datalyze

# View logs
sudo journalctl -u datalyze -f
```

---

## Uninstallation

### Remove the package

```bash
# Remove package (keeps config files)
sudo apt remove datalyze

# Remove package and config files
sudo apt purge datalyze
```

---

## Package Details

**Package Name:** datalyze  
**Version:** 1.0.0  
**Architecture:** all  
**Dependencies:** python3 (>= 3.8), python3-pip, libcairo2, libpango-1.0-0, libgdk-pixbuf2.0-0, libffi-dev, shared-mime-info

**Installed Files:**
- Application: `/opt/datalyze/`
- Service: `/etc/systemd/system/datalyze.service`
- CLI: `/usr/local/bin/datalyze`
- Desktop Entry: `/usr/share/applications/datalyze.desktop`

**Port:** 8081  
**URL:** http://localhost:8081

---

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u datalyze -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8081

# Manually test
cd /opt/datalyze
python3 app.py
```

### Dependencies missing

```bash
# Reinstall dependencies
cd /opt/datalyze
sudo pip3 install -r requirements.txt
```

### Permission issues

```bash
# Fix permissions
sudo chown -R root:root /opt/datalyze
sudo chmod -R 755 /opt/datalyze
```

---

## Features

✅ **Massive Dataset Support** - Handle files up to 25GB with streaming & DuckDB  
✅ **Modern UI** - Dark mode with glassmorphism  
✅ **Multiple Export Formats** - CSV, Excel, JSON, Parquet  
✅ **Correlation Analysis** - Numeric relationship detection  
✅ **Advanced Preprocessing** - Normalize, standardize, encode, outlier handling  
✅ **PDF Reports** - Comprehensive analysis reports in PDF format  
✅ **Auto-start on Boot** - Systemd service integration  

---

## Support

For issues or questions:
- Check logs: `datalyze logs`
- View status: `datalyze status`
- GitHub: [Your repository URL]
