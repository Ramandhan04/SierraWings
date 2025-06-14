# SierraWings Pixhawk Connection Guide

## Live Hardware Setup for Real Emergency Drone Operations

### Hardware Requirements
- Pixhawk flight controller (PX4 or ArduPilot firmware)
- Raspberry Pi 4 with wireless connectivity  
- Telemetry radio modules (optional, for long-range)
- GPS module with external antenna
- Power module for voltage/current sensing

### Connection Methods

#### 1. Direct USB Connection
```bash
# Connect Pixhawk via USB cable
# Device appears as: /dev/ttyUSB0 or /dev/ttyACM0
```

#### 2. UART/Serial Connection (Raspberry Pi)
```bash
# Connect to Raspberry Pi GPIO UART pins
# Device: /dev/ttyAMA0 or /dev/serial0
# Baud rate: 57600 or 921600
```

#### 3. Network/WiFi Connection
```bash
# Pixhawk with WiFi telemetry module
# Connection: IP:PORT (e.g., 192.168.1.100:14550)
```

### Live System Configuration

#### 1. Raspberry Pi Drone Setup
Each drone requires a Raspberry Pi running the drone service:

```python
# On each Raspberry Pi drone
from raspberry_pi_drone import RaspberryPiDrone

# Initialize with your Pixhawk connection
drone = RaspberryPiDrone("Sierra-1", "/dev/ttyUSB0")
drone.start_service()  # Starts live telemetry broadcast
```

#### 2. Ground Control Station
The main SierraWings server discovers and tracks all drones:

```python
# Main server automatically discovers drones
# Live tracking at: /admin/drones/live-tracking
```

### Real-Time Features

#### Live Telemetry Data
- GPS coordinates with 1-meter accuracy
- Battery voltage and remaining capacity
- Flight mode and armed status
- Signal strength and connection quality
- Wind speed and direction
- Altitude and ground speed

#### Emergency Commands
- ARM/DISARM drone remotely
- Emergency return-to-launch (RTL)
- Mission abort and safety landing
- Real-time flight path adjustments

### Network Discovery Protocol

The system uses UDP broadcast for automatic drone discovery:

```
Port 8888: Drone discovery service
- Drones announce themselves every 5 seconds
- Include GPS position, battery, and status
- Ground station maintains live connection list
```

### Live GPS Tracking

#### Coordinate System
- WGS84 datum (standard GPS coordinates)
- Precision: 6 decimal places (1-meter accuracy)
- Real-time updates every 1-2 seconds

#### Map Integration
- Leaflet.js with OpenStreetMap tiles
- Sierra Leone geographic boundaries
- Live drone markers with status colors
- Flight path recording and replay

### Emergency Protocols

#### 1. Communication Loss
- Automatic return-to-launch after 30 seconds
- Battery failsafe at 20% charge
- GPS failsafe if signal lost

#### 2. Medical Emergency Priority
- Priority mission queue for emergency calls
- Automatic route optimization
- Real-time ETA calculations

### Testing Live Connections

Run the system test to verify hardware connectivity:

```bash
python test_live_system.py
```

This will:
- Test drone discovery service
- Attempt Pixhawk connections
- Verify telemetry data flow
- Check system readiness

### Production Deployment

#### Drone Fleet Setup
1. Install Raspberry Pi on each drone
2. Configure Pixhawk connection string
3. Set unique drone ID and registration
4. Test GPS accuracy and radio range

#### Ground Station
1. Deploy SierraWings web application
2. Configure PostgreSQL database
3. Set up live tracking dashboard
4. Train operators on emergency procedures

### Troubleshooting

#### No Drones Discovered
- Check network connectivity
- Verify port 8888 not blocked
- Ensure drone service running
- Test GPS signal strength

#### Poor GPS Accuracy
- Check antenna placement
- Verify satellite count (need 6+ for 3D fix)
- Test different GPS modules
- Consider RTK for centimeter accuracy

#### Connection Timeouts
- Check cable connections
- Verify baud rate settings
- Test different USB ports
- Monitor system resources

This system is designed for real emergency medical operations in Sierra Leone, providing authentic live tracking and control of actual drone hardware.