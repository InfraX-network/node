# InfraX Node

InfraX Node is a python based application that is intended to run in the background and process App and Job requests from the InfraX Router. It is responsible for managing the execution of the Apps and Jobs on the local machine and uploading the results back to the InfraX Router.

## Installation

The InfraX Node software is designed to run on Linux based operating systems. If you are using a different operating system, you may need to set up a virtual machine or container to run the software.

1. Edit the `config.toml` file to match your information.
2. Use the `install.sh` script to install the InfraX Node on your machine. The script will install the required dependencies, install, and start the InfraX Node service.

    ```bash
    sudo ./install.sh
    ```

_Warning: Because the InfraX Node software is designed to accept external requests, it is important to ensure that your firewall settings allow incoming connections on the specified port (default `external_port=8420`). If you are running the software on a cloud server, you may need to configure the security group settings to allow incoming connections on the specified port._

## Usage

Once your node is connected to the InfraX network, requests to install Apps and run Jobs will be sent to your node. You can view the status of your node and the Jobs that are currently running by visiting the InfraX dashboard.

## Mangement

The InfraX Node software comes with a management script that can be used to update the software and restart the node. To update the software, run the following command:

```bash
sudo ./manage.sh update
```

This will pull the latest version of the software from the repository and restart the node.

Additional commands can be found by running the following command:

```bash
sudo ./manage.sh help
```

## License

[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
