
import json
import logging
import os
import sys

# from botocore.config import Config
from datetime import datetime

sys.path.append(os.environ['GIT_HOME']) # point of entry to GIT
from iagcl.geo_utilities.devopsutils import awsutils
from iagcl.geo_utilities.devopsutils import sshutils


# #########################################################################################################
# debugging params

ON_IAG_NETWORK = False
CREATE_INSTANCE = True

# EXTERNAL_IP_ADDRESS = "168.140.181.4/32"  # IAG
# EXTERNAL_IP_ADDRESS = "101.164.227.2/32"  # HS home
# EXTERNAL_IP_ADDRESS = "1.144.97.34/32"  # LocEng Telstra iPhone
EXTERNAL_IP_ADDRESS = "49.180.155.194/32"  # HS Optus iPhone
# EXTERNAL_IP_ADDRESS = ""  # LocEng iPhone

# #########################################################################################################

if ON_IAG_NETWORK:
    from iagcl.geo_utilities.environment.interface import Interface_Suite

logging.getLogger("paramiko").setLevel(logging.INFO)

OWNER = "s57405"
# PRINCIPAL = "arn:aws:iam::310933283416:user/s57405"
S3_BUCKET = "s57405"
AMI_ID = "ami-bb1901d8"  # Ubuntu 16.04 LTS - see https://cloud-images.ubuntu.com/locator/ec2/
BUILD_ID = "t2.micro"
AVAILABILITY_ZONE = "ap-southeast-2"  # Sydney, AU
PEM_FILE = "/Users/hugh/.aws/loceng-key.pem"
KEY_NAME = "loceng-key"
INSTANCE_NAMES = ["loceng CoR database"]

# list of instances to terminate & create
EC2_INSTANCE_DICTS = [
    # {"name": "loceng CoR web server",
    #  "external_ip": EXTERNAL_IP_ADDRESS,
    # "availability_zone": AVAILABILITY_ZONE,
    #                      "ami_id": AMI_ID,
    # "build_id": BUILD_ID,
    #  "security_groups": [
    #      {"name": "public_ssh", "type": "public", "port": 22, "delete_after_build": True},     # ssh
    #      {"name": "private_https", "type": "private", "port": 443, "delete_after_build": False}]  # https
    #  },
    {"name": "loceng CoR database",
     "owner": OWNER,
     "purpose": "LocEng Choice of Repairer testing",
     "external_ip": EXTERNAL_IP_ADDRESS,
     "availability_zone": AVAILABILITY_ZONE,
     "ami_id": AMI_ID,
     "build_id": BUILD_ID,
     "pem_file": PEM_FILE,
     "key_name": KEY_NAME,
     "security_groups": [
            # {"name": "public_postgres", "type": "public", "port": 5432, "delete_after_build": False},  # postgres
            {"name": "private_postgres", "type": "private", "port": 5432, "delete_after_build": False},  # postgres
            {"name": "public_ssh", "type": "public", "port": 22, "delete_after_build": True},     # ssh
            # {"name": "public_http", "type": "public", "port": 80, "delete_after_build": False}  # postgres
            # {"name": "public_https", "type": "public", "port": 443, "delete_after_build": False}  # postgres
        ]
     }
]

CONF_FILE = os.path.dirname(os.path.abspath(__file__)) + "/ec2.json"


def main():
    full_start_time = datetime.now()

    # get proxy settings from passwords.ini file
    if ON_IAG_NETWORK:
        proxy = passwords.proxies["https"]
    else:
        proxy = None

    # get EC2 client and service resources
    client, resources = awsutils.init(logger, AVAILABILITY_ZONE, False, "https", proxy)
    if resources is None:
        return False

    # get VPC details
    vpc_id, subnet_id, ipv4_cidr = awsutils.vpc_details(logger, resources)
    if ipv4_cidr is None:
        return False

    # create EC2 instance after cleaning up old resources (NOT PROD GRADE CI CODE)
    if CREATE_INSTANCE:
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
    else:
        file = open(CONF_FILE, 'r')
        ec2_dicts = json.loads(file.read())
        file.close()

        print(ec2_dicts)

    logger.info("")

    # # copy data & code to S3 (for copying to EC2 instance in bash script)
    # path = os.path.dirname(os.path.realpath(__file__)) + os.sep + ".." + os.sep + ".." + os.sep + "map_services" + os.sep
    #
    # awsutils.copy_file_to_s3(path + "wsgi.py", S3_BUCKET, "wsgi.py")
    # awsutils.copy_file_to_s3(path + "map_services", S3_BUCKET, "map_services")
    # awsutils.copy_file_to_s3(path + "map_services.py", S3_BUCKET, "map_services.py")
    # awsutils.copy_file_to_s3(path + "map_services.ini", S3_BUCKET, "map_services.ini")
    # awsutils.copy_file_to_s3(path + "map_services.service", S3_BUCKET, "map_services.service")
    # awsutils.copy_file_to_s3(path + "sample_google_map.html", S3_BUCKET, "sample_google_map.html")

    # TODO: replace the GeoJSON URL in the sample Google Map with the EC2 one

    # connect to instances via SSH and run bash scripts (only works from outside of IAG network)
    for ec2_dict in ec2_dicts:
        if not ON_IAG_NETWORK:
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

            # TODO: rebuild the repairer locality table and dump the cor schema, and copy to S3

            # TODO: test the API is working and the response is valid

            # # data and code loaded - run the thing using gunicorn!
            # cmd = "sudo gunicorn -w {0} -D --pythonpath ~/ -b 0.0.0.0:80 map_services:app" \
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
        else:
            logger.info("EC2 instance ID      : {}".format(ec2_dict["id"]))
            logger.info("")
            logger.info("Private IP address   : {}".format(ec2_dict["private_ip"]))
            logger.info("Public IP address    : {}".format(ec2_dict["public_ip"]))
            logger.info("")
            logger.info("Total time : {0}".format(datetime.now() - full_start_time))
            logger.info("")

    return True


if __name__ == '__main__':
    if ON_IAG_NETWORK:
        passwords, logger, heartbeat = Interface_Suite(log_file=None)
    else:
        # set logger
        logger = logging.getLogger()
        log_file = os.path.abspath(__file__).replace(".py", ".log")
        logging.basicConfig(filename=log_file, level=logging.DEBUG, format="%(asctime)s %(message)s",
                            datefmt="%m/%d/%Y %I:%M:%S %p")

        # setup logger to write to screen as well as writing to log file
        # define a Handler which writes INFO messages or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

    logger.info("")
    logger.info("Start EC2 deployment")

    if main():
        logger.info("Finished successfully!")
    else:
        logger.fatal("Something bad happened!")

    logger.info("")
    logger.info("-------------------------------------------------------------------------------")
