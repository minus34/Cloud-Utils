


import json
import logging
import os

# from botocore.config import Config
from datetime import datetime

from aws import awsutils
import pwdutils
import sshutils

logging.getLogger("paramiko").setLevel(logging.INFO)


def build_servers(settings, logger, proxy=None):
    full_start_time = datetime.now()

    # get EC2 client and service resources
    client, resources = awsutils.init(logger, AVAILABILITY_ZONE, False, "https", proxy)
    if resources is None:
        return False

    # get VPC details
    vpc_id, subnet_id, ipv4_cidr = awsutils.vpc_details(logger, resources)
    if ipv4_cidr is None:
        return False

    # create EC2 instance after cleaning up old resources (NOT PROD GRADE CI CODE)

    # delete EC2 instance(s) with the same names, as well as the Elastic IPs assigned to them
    if not awsutils.terminate_ec2_instances(logger, client, resources, EC2_INSTANCE_DICTS):
        return False

    # OPTIONAL - delete security groups. Useful if changing the external IP address (e.g from Home to Work)
    if not awsutils.delete_security_groups(logger, client, EC2_INSTANCE_DICTS):
        return False

    # create instance, along with elastic IP and SecurityGroup(s)
    ec2_dicts = awsutils.create_ec2_instance(logger, client, resources, EC2_INSTANCE_DICTS,
                                             vpc_id, subnet_id, ipv4_cidr)
    if ec2_dicts is None:
        return False

    # write the important bits to a conf file
    file = open(CONF_FILE, 'w')
    file.write(json.dumps(ec2_dicts))
    file.close()

    logger.info("")

    # # copy data & code to S3 (for copying to EC2 instance in bash script)
    # path = os.path.dirname(os.path.realpath(__file__)) + os.sep + ".." + os.sep + ".." + os.sep + "map_services" + os.sep
    # awsutils.copy_file_to_s3(path + "wsgi.py", S3_BUCKET, "wsgi.py")

    # connect to instances via SSH and run bash scripts (only works from outside of IAG network)
    for ec2_dict in ec2_dicts:
        # get SSH connection
        ssh_client = sshutils.get_ssh_connection(logger, ec2_dict["public_ip"], PEM_FILE)
        if ssh_client is None:
            return False

        # get passwords
        admin_password = ec2_dict["admin_password"]
        readonly_password = ec2_dict["readonly_password"]

        # update & upgrade instance and reboot
        if not sshutils.update_upgrade_instance(logger, ssh_client, ec2_dict["id"]):
            return False

        # get SSH connection (again, post-reboot)
        ssh_client = sshutils.get_ssh_connection(logger, ec2_dict["public_ip"], PEM_FILE)
        if ssh_client is None:
            return False

        # setup awscli tools on instance (note: the AWS credentials will be deleted at the end of this script)
        if not awsutils.install_awscli_tools(logger, ssh_client):
            return False

        # run each bash command
        bash_file = os.path.abspath(__file__).replace(".py", ".sh")
        bash_script = open(bash_file, 'r').read()\
            .format(admin_password, readonly_password, ipv4_cidr, ec2_dict["public_ip"])
        bash_commands = bash_script.split("\n")

        for cmd in bash_commands:
            if cmd[:1] != "#" and cmd[:1].strip(" ") != "":  # ignore comments and blank lines
                sshutils.run_command(logger, ssh_client, cmd, admin_password)

        # delete AWS credentials file securely
        sshutils.run_command(logger, ssh_client, "sudo shred -n 200 -z -u ~/.aws/credentials")

        # TODO: test the thing is working and the response is valid

        # # data and code loaded - run the thing using gunicorn!

        # cd ../geo_programme/events/major_events_service/pif_extract/
        # sudo gunicorn  -w {0} server:app -p server.pid -b 127.0.0.1:8081 -D

        # cmd = "sudo gunicorn -w {0} -D --pythonpath ~/ -b 127.0.0.1:80 map_services:app" \
        #     .format(2)
        #     # .format(cpu_count * 2)
        # sshutils.run_command(logger, ssh_client, cmd)

        ssh_client.close()

        # TODO: delete port 22 security group at the end (for better security)

        logger.info("EC2 instance ID      : {}".format(ec2_dict["id"]))
        logger.info("")
        logger.info("Private IP address   : {}".format(ec2_dict["private_ip"]))
        logger.info("Public IP address    : {}".format(ec2_dict["public_ip"]))
        logger.info("")
        logger.info("PG Admin password    : {}".format(admin_password))
        logger.info("PG Readonly password : {}".format(readonly_password))
        logger.info("")
        logger.info("Total time : {0}".format(datetime.now() - full_start_time))
        logger.info("")

    return True

