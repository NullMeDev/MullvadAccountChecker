# NullVad Account Checker V5

A GUI application for checking Mullvad VPN account validity with proxy support, created by nullme.dev.

## Features

- Check multiple Mullvad accounts
- Proxy support (HTTP, HTTPS, SOCKS4, SOCKS5)
- Configurable delay between checks
- Detailed logging and error reporting
- Dark theme UI
- Save results to file

## Requirements

- Python 3.10 or higher
- PyQt6
- Mullvad CLI installed on your system

## Installation

All required dependencies are included in the package.

## Running the Application

Simply double-click the `run.bat` file to start the application.

## Usage

1. Click "Load Accounts" to load your account numbers from a text file
2. Configure proxy settings if needed (Settings -> Proxy Settings)
3. Adjust check delay if needed (Settings -> Set Delay)
4. Click "Start Checking" to begin checking accounts
5. Valid accounts will be saved to `nullvad_working.txt`

## Error Reporting

If you encounter any issues:
1. Go to Help -> Send Error Report
2. Copy the error report
3. Send it to null@nullme.dev

## Support

For support or bug reports, please contact: null@nullme.dev

## License

MIT License

Copyright (c) 2024 nullme.dev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
