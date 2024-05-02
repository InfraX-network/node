# InfraX Node

InfraX Node is a python based application that is intended to run in the background and process App and Job requests from the InfraX Router. It is responsible for managing the execution of the Apps and Jobs on the local machine and uploading the results back to the InfraX Router.

## Installation

Use the `install.sh` script to install the InfraX Node on your machine. The script will install the required dependencies, install, and start the InfraX Node service.

```bash
./install.sh
```

## Usage

The InfraX Node service can be started, stopped, and restarted using the following commands:

```bash
sudo systemctl start infrax-node
sudo systemctl stop infrax-node
sudo systemctl restart infrax-node
```

## License

[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
