#!/usr/bin/env python3
"""
SierraWings Raspberry Pi Drone Client
This script runs on Raspberry Pi connected to Pixhawk flight controller
"""

import socket
import json
import threading
import time
import logging
from datetime import datetime
from pymavlink import mavutil
import subprocess
import os

class RaspberryPiDroneClient:
    """Raspberry Pi client that connects to Pixhawk and communicates with SierraWings server"""
    
    def __init__(self, drone_id=None, pixhawk_connection='/dev/ttyACM0'):
        self.drone_id = drone_id or self._generate_drone_id()
        self.pixhawk_connection = pixhawk_connection
        self.server_ip = None
        self.server_port = 8888
        self.mavlink = None
        self.running = False
        self.announce_thread = None
        self.command_thread = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _generate_drone_id(self):
        """Generate unique drone ID based on Raspberry Pi serial"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        serial = line.split(':')[1].strip()
                        return f"SW-{serial[-8:].upper()}"
        except:
            pass
        return f"SW-{int(time.time())}"
    
    def connect_to_pixhawk(self):
        """Connect to Pixhawk flight controller"""
        try:
            self.logger.info(f"Connecting to Pixhawk on {self.pixhawk_connection}")
            self.mavlink = mavutil.mavlink_connection(self.pixhawk_connection, baud=57600)
            
            # Wait for heartbeat
            self.logger.info("Waiting for heartbeat...")
            heartbeat = self.mavlink.wait_heartbeat(timeout=10)
            
            if heartbeat:
                self.logger.info("Pixhawk connection established")
                return True
            else:
                self.logger.error("No heartbeat received from Pixhawk")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Pixhawk: {e}")
            return False
    
    def start_client(self):
        """Start the drone client"""
        if not self.connect_to_pixhawk():
            return False
            
        self.running = True
        
        # Start announcement thread
        self.announce_thread = threading.Thread(target=self._announcement_loop)
        self.announce_thread.daemon = True
        self.announce_thread.start()
        
        # Start command listener thread
        self.command_thread = threading.Thread(target=self._command_listener)
        self.command_thread.daemon = True
        self.command_thread.start()
        
        self.logger.info(f"Drone client {self.drone_id} started")
        return True
    
    def stop_client(self):
        """Stop the drone client"""
        self.running = False
        if self.mavlink:
            self.mavlink.close()
    
    def _announcement_loop(self):
        """Send periodic announcements to discover server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                # Get current telemetry
                telemetry = self._get_current_telemetry()
                
                announcement = {
                    'type': 'drone_announce',
                    'drone_id': self.drone_id,
                    'name': f'SierraWings-{self.drone_id}',
                    'port': 14550,
                    'pixhawk_status': 'connected' if self.mavlink else 'disconnected',
                    'firmware_version': self._get_firmware_version(),
                    'battery_voltage': telemetry.get('battery_voltage', 0),
                    'gps_fix': telemetry.get('gps_fix', False),
                    'flight_mode': telemetry.get('flight_mode', 'unknown'),
                    'armed': telemetry.get('armed', False),
                    'signal_strength': self._get_wifi_signal_strength(),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Broadcast announcement
                message = json.dumps(announcement).encode()
                sock.sendto(message, ('<broadcast>', self.server_port))
                
                self.logger.debug(f"Sent announcement for {self.drone_id}")
                
            except Exception as e:
                self.logger.error(f"Announcement error: {e}")
            
            time.sleep(5)  # Announce every 5 seconds
        
        sock.close()
    
    def _command_listener(self):
        """Listen for commands from server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 14550))
        sock.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                command = json.loads(data.decode())
                
                if command.get('target_drone') == self.drone_id:
                    self._handle_command(command, addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Command listener error: {e}")
        
        sock.close()
    
    def _handle_command(self, command, addr):
        """Handle incoming command"""
        try:
            cmd_type = command.get('command')
            params = command.get('params', {})
            
            self.logger.info(f"Received command: {cmd_type}")
            
            if cmd_type == 'arm':
                result = self._arm_drone()
            elif cmd_type == 'disarm':
                result = self._disarm_drone()
            elif cmd_type == 'takeoff':
                altitude = params.get('altitude', 10)
                result = self._takeoff(altitude)
            elif cmd_type == 'land':
                result = self._land()
            elif cmd_type == 'return_to_launch':
                result = self._return_to_launch()
            elif cmd_type == 'get_telemetry':
                result = self._get_current_telemetry()
            else:
                result = {'success': False, 'error': f'Unknown command: {cmd_type}'}
            
            # Send response
            response = {
                'drone_id': self.drone_id,
                'command': cmd_type,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(response).encode(), addr)
            sock.close()
            
        except Exception as e:
            self.logger.error(f"Command handling error: {e}")
    
    def _arm_drone(self):
        """Arm the drone"""
        try:
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 1, 0, 0, 0, 0, 0, 0
            )
            return {'success': True, 'message': 'Arm command sent'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _disarm_drone(self):
        """Disarm the drone"""
        try:
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            return {'success': True, 'message': 'Disarm command sent'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _takeoff(self, altitude):
        """Takeoff to specified altitude"""
        try:
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0, 0, 0, 0, 0, 0, 0, altitude
            )
            return {'success': True, 'message': f'Takeoff command sent to {altitude}m'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _land(self):
        """Land the drone"""
        try:
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            return {'success': True, 'message': 'Land command sent'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _return_to_launch(self):
        """Return to launch position"""
        try:
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            return {'success': True, 'message': 'RTL command sent'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_current_telemetry(self):
        """Get current telemetry from Pixhawk"""
        try:
            if not self.mavlink:
                return {}
            
            # Get latest messages (non-blocking)
            attitude = self.mavlink.recv_match(type='ATTITUDE', blocking=False)
            gps = self.mavlink.recv_match(type='GLOBAL_POSITION_INT', blocking=False)
            battery = self.mavlink.recv_match(type='SYS_STATUS', blocking=False)
            heartbeat = self.mavlink.recv_match(type='HEARTBEAT', blocking=False)
            
            telemetry = {
                'battery_voltage': battery.voltage_battery / 1000 if battery else 0,
                'battery_current': battery.current_battery / 100 if battery else 0,
                'battery_remaining': battery.battery_remaining if battery else 0,
                'gps_fix': gps.fix_type >= 3 if gps else False,
                'latitude': gps.lat / 1e7 if gps else 0,
                'longitude': gps.lon / 1e7 if gps else 0,
                'altitude': gps.alt / 1000 if gps else 0,
                'relative_altitude': gps.relative_alt / 1000 if gps else 0,
                'armed': bool(heartbeat.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) if heartbeat else False,
                'flight_mode': mavutil.mode_string_v10(heartbeat) if heartbeat else 'unknown',
                'system_status': heartbeat.system_status if heartbeat else 0,
                'roll': attitude.roll if attitude else 0,
                'pitch': attitude.pitch if attitude else 0,
                'yaw': attitude.yaw if attitude else 0
            }
            
            return telemetry
            
        except Exception as e:
            self.logger.error(f"Telemetry error: {e}")
            return {}
    
    def _get_firmware_version(self):
        """Get Pixhawk firmware version"""
        try:
            # Request autopilot version
            self.mavlink.mav.command_long_send(
                self.mavlink.target_system,
                self.mavlink.target_component,
                mavutil.mavlink.MAV_CMD_REQUEST_AUTOPILOT_CAPABILITIES,
                0, 1, 0, 0, 0, 0, 0, 0
            )
            
            # Wait for response
            if self.mavlink and hasattr(self.mavlink, 'recv_match'):
                msg = self.mavlink.recv_match(type='AUTOPILOT_VERSION', blocking=True, timeout=5)
            else:
                msg = None
            if msg:
                return f"PX4 v{msg.flight_sw_version}"
            
        except Exception as e:
            self.logger.error(f"Firmware version error: {e}")
        
        return "Unknown"
    
    def _get_wifi_signal_strength(self):
        """Get WiFi signal strength"""
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'Signal level' in line:
                    # Extract signal strength
                    signal = line.split('Signal level=')[1].split(' ')[0]
                    if 'dBm' in signal:
                        dbm = int(signal.replace('dBm', ''))
                        # Convert dBm to percentage (rough approximation)
                        return max(0, min(100, (dbm + 100) * 2))
        except:
            pass
        
        return 85  # Default signal strength

def main():
    """Main function to run the drone client"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SierraWings Raspberry Pi Drone Client')
    parser.add_argument('--drone-id', help='Drone ID (auto-generated if not provided)')
    parser.add_argument('--pixhawk', default='/dev/ttyACM0', help='Pixhawk connection string')
    args = parser.parse_args()
    
    client = RaspberryPiDroneClient(args.drone_id, args.pixhawk)
    
    try:
        if client.start_client():
            print(f"Drone client {client.drone_id} running...")
            print("Press Ctrl+C to stop")
            
            while client.running:
                time.sleep(1)
        else:
            print("Failed to start drone client")
            
    except KeyboardInterrupt:
        print("\nStopping drone client...")
        client.stop_client()

if __name__ == '__main__':
    main()