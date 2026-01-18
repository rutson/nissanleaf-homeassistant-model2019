# Nissan Connect Home Assistant Integration

A custom Home Assistant integration for Nissan Connect that provides real-time battery and charging information for Nissan electric vehicles.
This software is an API for Nissan Leaf cars as of Model 2019. 
Original algorithm from Carwingsflutter (Tobiaswk/carwingsfluitter)
Rebuilt in Python for Homeassistant.

## Features

This integration provides comprehensive battery monitoring for Nissan electric vehicles through the Nissan Connect service. It polls data every 15 minutes and provides the following sensors for each vehicle:

### Battery & Range Sensors
- **Battery Level**: Current battery charge percentage
- **Range (HVAC Off)**: Estimated range with climate control off (km)
- **Range (HVAC On)**: Estimated range with climate control on (km)
- **Battery Bar Level**: Raw battery bar indicator
- **Battery Capacity**: Total battery capacity (kWh)

### Charging Sensors
- **Charge Power**: Current charging power (kW)
- **Charge Status**: Current charging state
- **Plug Status**: Whether the vehicle is plugged in
- **Plug Status Detail**: Detailed plug connection information
- **Time to Full (Slow)**: Time required for full charge on slow charger (minutes)
- **Time to Full (Normal)**: Time required for full charge on normal charger (minutes)
- **Time to Full (Fast)**: Time required for full charge on fast charger (minutes)

### General Information
- **Last Update Time**: Timestamp of the last data update

## Installation

### Method 1: Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/nissan_connect/` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

### Method 2: HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS
3. Install the "Nissan Connect" integration through HACS
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Nissan Connect" and select it
3. Enter your Nissan Connect credentials:
   - **Username**: Your Nissan Connect email address
   - **Password**: Your Nissan Connect password
4. Click **Submit**

The integration will automatically discover all vehicles associated with your Nissan Connect account.

## Requirements

- Home Assistant 2021.3.0 or later
- Valid Nissan Connect account
- Nissan electric vehicle (LEAF, Ariya, etc.) enrolled in Nissan Connect
- `aiohttp` Python package (automatically installed)

## Supported Vehicles

This integration is designed to work with Nissan electric vehicles that support the Nissan Connect service, including:
- Nissan LEAF
- Nissan Ariya
- Other Nissan EVs with Connect support

## Data Updates

- Data is polled every 15 minutes to balance timeliness with API rate limits
- All sensors update simultaneously during each polling cycle
- Failed updates are logged and retried on the next cycle

## Troubleshooting

### Authentication Issues

**Problem**: "Authentication failed" error during setup
**Solutions**:
- Verify your Nissan Connect username and password
- Ensure your account is active and not locked
- Check if Nissan Connect service is available in your region
- Try logging into the Nissan Connect app/website manually first

### No Vehicles Found

**Problem**: Setup succeeds but no vehicles are discovered
**Solutions**:
- Ensure your Nissan electric vehicle is properly enrolled in Nissan Connect
- Verify the vehicle has an active data plan
- Check that the vehicle is connected to the internet
- Try removing and re-adding the integration

### Missing Data

**Problem**: Some sensors show "unavailable" or no data
**Solutions**:
- Wait for the next data update cycle (up to 15 minutes)
- Check vehicle connectivity and Nissan Connect service status
- Ensure the vehicle has been driven recently to refresh data
- Verify that the specific feature is supported by your vehicle model

### API Errors

**Problem**: Frequent "Error fetching data" messages in logs
**Solutions**:
- Check Nissan Connect service status
- Reduce polling frequency if needed (requires code modification)
- Ensure stable internet connection
- Monitor for Nissan API outages

## Development

This integration consists of several key files:

- `__init__.py`: Main integration setup and lifecycle management
- `api.py`: Async API client for Nissan Connect/Kamereon API
- `config_flow.py`: Configuration flow for user setup
- `sensor.py`: Sensor platform implementation
- `manifest.json`: Integration metadata

### Testing Script

The repository includes `get_vehicle_info.py`, a standalone Python script for testing the Nissan Connect API outside of Home Assistant. This can be useful for:

- Testing API connectivity
- Debugging authentication issues
- Understanding available vehicle data
- Development and troubleshooting

Usage:
```bash
python get_vehicle_info.py
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not officially affiliated with Nissan Motor Corporation. Use at your own risk. The developers are not responsible for any issues that may arise from using this integration.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review Home Assistant logs for error messages
3. Create an issue on the GitHub repository
4. Check Nissan Connect service status

## Version History

- **1.0.0**: Initial release with basic battery monitoring sensors</content>
<parameter name="filePath">c:\python\nissan\README.md