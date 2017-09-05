#
# utilities for running SSH commands on remote computers
#

import os
import paramiko
import time

from datetime import datetime

BASH_DIRECTORY = os.path.dirname(os.path.abspath(__file__)) + os.sep + "bash_scripts" + os.sep


# create an SSH connection to a remote computer using Paramiko
def get_ssh_connection(logger, ip_address, pem_file, user_name):

    try:
        key = paramiko.RSAKey.from_private_key_file(pem_file)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect to EC2 instance via SSH
        ssh_client.connect(
            hostname=ip_address,
            username=user_name,
            pkey=key
        )

        logger.info("Connected to {} via SSH".format(ip_address))
        logger.info("")

        return ssh_client

    except Exception as ex:
        logger.fatal("Couldn't create SSH connection to {0} : {1}".format(ip_address, ex))
        return None


def open_bash_script(logger, bash_file):

    output_commands = list()

    try:
        bash_script = open(bash_file, 'r').read()
        commands = bash_script.split("\n")
        for cmd in commands:
            if cmd[:1] != "#" and cmd[:1].strip(" ") != "":  # ignore comments and blank lines
                output_commands.append(cmd)

        return output_commands
    except Exception as ex:
        logger.fatal("Couldn't open {0} : {1}".format(bash_file, ex))
        return None


# run a single bash command
def run_command(logger, ssh_client, cmd, admin_password=None):
    start_time = datetime.now()

    # don't display aws keys in the log
    if "aws_access_key_id" in cmd:
        display_cmd = "export aws_access_key_id=****************************** >> ~/credentials"
    elif "aws_secret_access_key" in cmd:
        display_cmd = "export aws_secret_access_key=****************************** >> ~/credentials"
    else:
        display_cmd = cmd

    logger.info("START : {0}".format(display_cmd))

    # run command
    stdin, stdout, stderr = ssh_client.exec_command(cmd)

    # send Postgres user password to stdin to run pg_restore
    if "pg_restore" in cmd:
        stdin.write(admin_password + '\n')
        stdin.flush()

    stdin.close()

    for whocares in stdout.read().splitlines():
        pass
    stdout.close()

    for line in stderr.read().splitlines():
        if line:
            logger.info("\t\t{0}".format(line))
    stderr.close()

    logger.info("END   : {0} : {1}".format(display_cmd, datetime.now() - start_time))
    logger.info("")


# run update and upgrade on remote computer and reboot
def update_upgrade_instance(logger, ssh_client, instance_id, reboot_time=60):
    try:
        bash_commands = open_bash_script(logger, BASH_DIRECTORY + "update_upgrade.sh")

        if bash_commands:
            for cmd in bash_commands:
                run_command(logger, ssh_client, cmd)

            logger.info("EC2 instance {} updated & upgraded".format(instance_id))
            logger.info("")

            # # reboot and wait for restart
            # run_command(logger, ssh_client, "sudo reboot")

            logger.info("Waiting 60s for instance to reboot...")
            time.sleep(reboot_time)

            return True
        else:
            return False

    except Exception as ex:
        logger.fatal("Couldn't update & upgrade and reboot {0} : {1}".format(instance_id, ex))
        return False
