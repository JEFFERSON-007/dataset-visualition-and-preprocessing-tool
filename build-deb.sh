#!/bin/bash
# Build Debian package for Dataset Visualization Tool

set -e

PACKAGE_NAME="datalyze"
VERSION="1.0.0"
ARCH="all"
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package: ${PACKAGE_NAME} v${VERSION}"

# Clean previous builds
rm -rf build
mkdir -p "$BUILD_DIR"

# Create directory structure
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/datalyze"
mkdir -p "$BUILD_DIR/etc/systemd/system"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/local/bin"

# Copy application files
echo "Copying application files..."
cp app.py "$BUILD_DIR/opt/datalyze/"
cp duckdb_backend.py "$BUILD_DIR/opt/datalyze/" 2>/dev/null || true
cp requirements.txt "$BUILD_DIR/opt/datalyze/"
cp -r static "$BUILD_DIR/opt/datalyze/"
cp README.md "$BUILD_DIR/opt/datalyze/"

# Create control file
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: datalyze
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.8), python3-pip, libcairo2, libpango-1.0-0, libpangocairo-1.0-0, libgdk-pixbuf2.0-0, libffi-dev, shared-mime-info
Maintainer: DataLyze Team <support@datalyze.local>
Description: DataLyze - Premium Dataset Visualization and Preprocessing Tool
 A powerful web-based tool for dataset analysis, visualization,
 and preprocessing. Supports CSV, Excel, JSON, and Parquet files
 up to 25GB with advanced features like correlation analysis,
 data cleaning, and multiple export formats.
 .
 Features:
  - Massive dataset support (up to 25GB) via streaming & DuckDB
  - Modern dark mode UI with Glassmorphism
  - Advanced preprocessing (normalize, standardize, encode)
  - Correlation matrix analysis
  - PDF Report Generation
  - Multiple export formats (CSV, Excel, JSON, Parquet)
EOF

# Create postinst script
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

echo "Installing Python dependencies..."
cd /opt/datalyze
pip3 install -r requirements.txt --quiet

echo "Creating systemd service..."
systemctl daemon-reload
systemctl enable datalyze.service

echo "Starting DataLyze service..."
systemctl start datalyze.service

echo ""
echo "✅ DataLyze installed successfully!"
echo ""
echo "🌐 Access the application at: http://localhost:8081"
echo ""
echo "📝 Useful commands:"
echo "  - Start service:   sudo systemctl start datalyze"
echo "  - Stop service:    sudo systemctl stop datalyze"
echo "  - Check status:    sudo systemctl status datalyze"
echo "  - View logs:       sudo journalctl -u datalyze -f"
echo ""

exit 0
EOF

# Create prerm script
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

echo "Stopping DataLyze service..."
systemctl stop datalyze.service || true
systemctl disable datalyze.service || true

exit 0
EOF

# Create postrm script
cat > "$BUILD_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    echo "Removing application files..."
    rm -rf /opt/datalyze
    systemctl daemon-reload
fi

exit 0
EOF

# Make scripts executable
chmod 755 "$BUILD_DIR/DEBIAN/postinst"
chmod 755 "$BUILD_DIR/DEBIAN/prerm"
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# Create systemd service file
cat > "$BUILD_DIR/etc/systemd/system/datalyze.service" << EOF
[Unit]
Description=DataLyze - Dataset Visualization and Preprocessing Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/datalyze
ExecStart=/usr/bin/python3 /opt/datalyze/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create desktop entry (optional)
cat > "$BUILD_DIR/usr/share/applications/datalyze.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DataLyze
Comment=Analyze and visualize datasets
Exec=xdg-open http://localhost:8081
Icon=utilities-system-monitor
Terminal=false
Categories=Development;Utility;
EOF

# Create command-line launcher
cat > "$BUILD_DIR/usr/local/bin/datalyze" << 'EOF'
#!/bin/bash
# DataLyze CLI

case "$1" in
    start)
        sudo systemctl start datalyze
        echo "✅ Service started. Access at http://localhost:8081"
        ;;
    stop)
        sudo systemctl stop datalyze
        echo "✅ Service stopped"
        ;;
    restart)
        sudo systemctl restart datalyze
        echo "✅ Service restarted"
        ;;
    status)
        systemctl status datalyze
        ;;
    logs)
        journalctl -u datalyze -f
        ;;
    open)
        xdg-open http://localhost:8081
        ;;
    *)
        echo "DataLyze v1.0.0"
        echo ""
        echo "Usage: datalyze {start|stop|restart|status|logs|open}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the service"
        echo "  stop     - Stop the service"
        echo "  restart  - Restart the service"
        echo "  status   - Check service status"
        echo "  logs     - View service logs"
        echo "  open     - Open in browser"
        exit 1
        ;;
esac
EOF

chmod 755 "$BUILD_DIR/usr/local/bin/datalyze"

# Fix line endings for Windows compatibility
if command -v dos2unix &> /dev/null; then
    find "$BUILD_DIR" -type f -exec dos2unix {} \;
else
    # Fallback with sed if dos2unix not available
    find "$BUILD_DIR" -type f -exec sed -i 's/\r$//' {} \;
fi

# Build the package
echo "Building package..."
dpkg-deb --build "$BUILD_DIR"

# Move to releases directory
mkdir -p releases
mv "build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" releases/

echo ""
echo "✅ Package built successfully!"
echo ""
echo "📦 Package: releases/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "📝 Installation:"
echo "  sudo dpkg -i releases/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "🗑️  Uninstallation:"
echo "  sudo apt remove datalyze"
echo ""
