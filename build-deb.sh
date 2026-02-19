#!/bin/bash
# Build Debian package for Dataset Visualization Tool

set -e

PACKAGE_NAME="dataset-viz"
VERSION="1.0.0"
ARCH="all"
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package: ${PACKAGE_NAME} v${VERSION}"

# Clean previous builds
rm -rf build
mkdir -p "$BUILD_DIR"

# Create directory structure
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/dataset-viz"
mkdir -p "$BUILD_DIR/etc/systemd/system"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/local/bin"

# Copy application files
echo "Copying application files..."
cp app.py "$BUILD_DIR/opt/dataset-viz/"
cp duckdb_backend.py "$BUILD_DIR/opt/dataset-viz/" 2>/dev/null || true
cp requirements.txt "$BUILD_DIR/opt/dataset-viz/"
cp -r static "$BUILD_DIR/opt/dataset-viz/"
cp README.md "$BUILD_DIR/opt/dataset-viz/"

# Create control file
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: dataset-viz
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.8), python3-pip
Maintainer: Dataset Viz Team <support@datasetviz.local>
Description: Dataset Visualization and Preprocessing Tool
 A powerful web-based tool for dataset analysis, visualization,
 and preprocessing. Supports CSV, Excel, JSON, and Parquet files
 up to 5GB with advanced features like correlation analysis,
 data cleaning, and multiple export formats.
 .
 Features:
  - Multi-GB dataset support (up to 5GB)
  - Modern dark mode UI
  - Advanced preprocessing (normalize, standardize, encode)
  - Correlation matrix analysis
  - Multiple export formats (CSV, Excel, JSON, Parquet)
  - HTML report generation
EOF

# Create postinst script
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

echo "Installing Python dependencies..."
cd /opt/dataset-viz
pip3 install -r requirements.txt --quiet

echo "Creating systemd service..."
systemctl daemon-reload
systemctl enable dataset-viz.service

echo "Starting Dataset Visualization service..."
systemctl start dataset-viz.service

echo ""
echo "✅ Dataset Visualization Tool installed successfully!"
echo ""
echo "🌐 Access the application at: http://localhost:8081"
echo ""
echo "📝 Useful commands:"
echo "  - Start service:   sudo systemctl start dataset-viz"
echo "  - Stop service:    sudo systemctl stop dataset-viz"
echo "  - Check status:    sudo systemctl status dataset-viz"
echo "  - View logs:       sudo journalctl -u dataset-viz -f"
echo ""

exit 0
EOF

# Create prerm script
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

echo "Stopping Dataset Visualization service..."
systemctl stop dataset-viz.service || true
systemctl disable dataset-viz.service || true

exit 0
EOF

# Create postrm script
cat > "$BUILD_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    echo "Removing application files..."
    rm -rf /opt/dataset-viz
    systemctl daemon-reload
fi

exit 0
EOF

# Make scripts executable
chmod 755 "$BUILD_DIR/DEBIAN/postinst"
chmod 755 "$BUILD_DIR/DEBIAN/prerm"
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# Create systemd service file
cat > "$BUILD_DIR/etc/systemd/system/dataset-viz.service" << EOF
[Unit]
Description=Dataset Visualization and Preprocessing Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/dataset-viz
ExecStart=/usr/bin/python3 /opt/dataset-viz/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create desktop entry (optional)
cat > "$BUILD_DIR/usr/share/applications/dataset-viz.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Dataset Visualization
Comment=Analyze and visualize datasets
Exec=xdg-open http://localhost:8081
Icon=utilities-system-monitor
Terminal=false
Categories=Development;Utility;
EOF

# Create command-line launcher
cat > "$BUILD_DIR/usr/local/bin/dataset-viz" << 'EOF'
#!/bin/bash
# Dataset Visualization Tool CLI

case "$1" in
    start)
        sudo systemctl start dataset-viz
        echo "✅ Service started. Access at http://localhost:8081"
        ;;
    stop)
        sudo systemctl stop dataset-viz
        echo "✅ Service stopped"
        ;;
    restart)
        sudo systemctl restart dataset-viz
        echo "✅ Service restarted"
        ;;
    status)
        systemctl status dataset-viz
        ;;
    logs)
        journalctl -u dataset-viz -f
        ;;
    open)
        xdg-open http://localhost:8081
        ;;
    *)
        echo "Dataset Visualization Tool v1.0.0"
        echo ""
        echo "Usage: dataset-viz {start|stop|restart|status|logs|open}"
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

chmod 755 "$BUILD_DIR/usr/local/bin/dataset-viz"

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
echo "  sudo apt remove dataset-viz"
echo ""
