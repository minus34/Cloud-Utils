
import boto3
import time
import sshutils

from botocore.config import Config


# create and return EC2 client and services resources
def init(logger, availability_zone, verify_certificate=True, protocol="https", proxy=None):

    try:
        if proxy is not None:
            # get ec2 client (ignoring IAG's invalid SSL certificate)
            client = boto3.client('ec2', verify=verify_certificate, region_name=availability_zone,
                                  config=Config(proxies={protocol: proxy}))

            # get ec2 service resources (ignoring IAG's invalid SSL certificate)
            resources = boto3.resource('ec2', verify=verify_certificate, region_name=availability_zone,
                                       config=Config(proxies={protocol: proxy}))
        else:
            client = boto3.client('ec2', region_name=availability_zone)
            resources = boto3.resource('ec2', region_name=availability_zone)

        logger.info("Got EC2 client & service resources")

        return client, resources
    except Exception as ex:
        logger.fatal("Couldn't get EC2 client & service resources: {}".format(ex))
        return None, None, None


# return vpc, subnet and IPv4 CIDR address range from the first VPC and subnet in their respective lists
def vpc_details(logger, resources):

    try:
        vpc = list(resources.vpcs.all())[0]
        vpc_id = vpc.id

        subnet = list(vpc.subnets.all())[0]
        subnet_id = subnet.id

        ipv4_cidr = vpc.cidr_block

        logger.info("Got VPC details - vpc_id: {0}, subnet_id: {1}, ipv4_cidr: {2}"
                    .format(vpc_id, subnet_id, ipv4_cidr))
        return vpc_id, subnet_id, ipv4_cidr

    except Exception as ex:
        logger.fatal("Couldn't get VPC details: {}".format(ex))
        return None, None, None


# terminate all EC2 instances with the chosen name, and release all Elastic IP addresses associated with them
def terminate_ec2_instances(logger, client, resources, instance_dicts):
    try:
        # get instances and Elastic IP addresses
        instance_collection = list(resources.instances.all())

        num_terminated = 0

        # terminate all instances and their Elastic IP addresses that match the instance name provided
        if len(instance_collection) > 0:
            for instance in instance_collection:
                if instance.tags is not None:
                    for tag in instance.tags:
                        if tag["Key"] == "Name":
                            for row in instance_dicts:
                                instance_name = row["name"]

                                if tag["Value"] == instance_name:
                                    instance_id = instance.id

                                    # release elastic IP address for instance
                                    if instance.public_ip_address is not None:
                                        if not release_elastic_ip(logger, client, instance_id):
                                            return False

                                    # terminate instance
                                    state = instance.state["Name"]
                                    if state != "terminated" and state != "shutting-down":
                                        logger.info("Terminating EC2 instance {0} ({1})"
                                                    .format(instance_name, instance_id))

                                        instance.terminate()
                                        num_terminated += 1

                                        # wait until instance is terminated to delete security group
                                        while state != "terminated":
                                            logger.info("Waiting 15s for instance to terminate. Current state is {}"
                                                        .format(state))
                                            time.sleep(15)
                                            curr_instance = resources.Instance(instance_id)
                                            state = curr_instance.state["Name"]

                                        logger.info("EC2 instance {0} ({1}) terminated"
                                                    .format(instance_name, instance_id))
                                        # wait a bit more for the security group to be become disassociated
                                        # time.sleep(15)

        if num_terminated == 0:
            logger.info("No EC2 instances to terminate")

        return True

    except Exception as ex:
        logger.fatal("Couldn't terminate instance(s): {}".format(ex))
        return False


# release elastic IP associated with an EC2 instance
def release_elastic_ip(logger, client, instance_id):

    addresses_list = list(client.describe_addresses()["Addresses"])

    # release Elastic IP address for the instance ID
    if len(addresses_list) > 0:
        for address in addresses_list:
            if address["InstanceId"] == instance_id:
                try:
                    client.disassociate_address(AssociationId=address['AssociationId'])
                    client.release_address(AllocationId=address['AllocationId'])

                    logger.info("Elastic IP {0} ({1}) disassociated & released"
                                .format(address["PublicIp"], address['AllocationId']))

                    return True

                except Exception as ex:
                    logger.fatal("Couldn't disassociate & release elastic IP {0} ({1}): {2}"
                                 .format(address["PublicIp"], address['AllocationId'], ex))
                    return False


# delete security groups. Useful if changing the external IP address (e.g from Home to Work)
def delete_security_groups(logger, client, instance_dicts):
    # get all security groups
    sg_dict = client.describe_security_groups()

    # get security groups assigned to instance(s)
    sg_names_to_delete = list()

    for instance_dict in instance_dicts:
        instance_sg_dicts = instance_dict["security_groups"]

        for instance_sg_dict in instance_sg_dicts:
            sg_names_to_delete.append(instance_sg_dict["name"])

    num_deleted = 0

    # delete security groups
    for sg_name in sg_names_to_delete:
        for sg in sg_dict["SecurityGroups"]:
            if sg["GroupName"] == sg_name:
                sg_id = sg["GroupId"]
                try:
                    client.delete_security_group(GroupId=sg_id)
                    num_deleted += 1
                    logger.info("Security group {0} ({1}) deleted".format(sg_name, sg_id))
                except Exception as ex:
                    logger.fatal("Couldn't delete security group {0} ({1}): {2}"
                                 .format(sg_name, sg_id, ex))
                    return False

    if num_deleted == 0:
        logger.info("No security groups to delete")

    return True


# create an EC2 instance and a SecurityGroup for it (if it doesn't exist)
def create_ec2_instance(logger, client, resources, instance_dicts, vpc_id, subnet_id, ipv4_cidr):

    # create security group(s)
    sg_dicts = create_security_groups(logger, client, instance_dicts, vpc_id, ipv4_cidr)

    if sg_dicts is None:
        logger.fatal("Not all security groups could be created - EC2 instance creation aborted")
        return False
    else:
        ec2_dicts = list()

        for instance_dict in instance_dicts:
            # get the security group IDs required for this instance
            sg_ids = list()
            for sg_dict in sg_dicts:
                for instance_sg_dict in instance_dict["security_groups"]:
                    if instance_sg_dict["name"] == sg_dict["name"]:
                        sg_ids.append(sg_dict["id"])

            # create EC2 instance
            try:
                response_dict = resources.create_instances(
                    ImageId=instance_dict["ami_id"],
                    MinCount=1,
                    MaxCount=1,
                    KeyName=instance_dict["key_name"],
                    InstanceType=instance_dict["build_id"],
                    SubnetId=subnet_id,
                    SecurityGroupIds=sg_ids,
                    Placement={"AvailabilityZone": instance_dict["availability_zone"] + "c"},
                    TagSpecifications=[
                        {
                            'ResourceType': "instance",
                            'Tags': [
                                {
                                    "Key": "Name",
                                    "Value": instance_dict["name"]
                                },
                                {
                                    "Key": "Owner",
                                    "Value": instance_dict["owner"]
                                },
                                {
                                    "Key": "Purpose",
                                    "Value": instance_dict["purpose"]
                                },
                            ]
                        },
                    ],
                    DryRun=False
                )

                # get instance info
                instance_id = response_dict[0].id
                instance_private_ip = response_dict[0].private_ip_address

                logger.info("EC2 instance {0} ({1}) created".format(instance_dict["name"], instance_id))
                logger.info("Private IP address: {0}".format(instance_private_ip))
            except Exception as ex:
                logger.fatal("Couldn't create EC2 instance  {0}: {1}".format(instance_dict["name"], ex))
                return None

            # wait until instance is running
            state = "pending"
            while state == "pending":
                logger.info("Waiting 10s for instance to start. Current state is {0}".format(state))
                time.sleep(10)
                instance = resources.Instance(instance_id)
                state = instance.state["Name"]

            # get a public IP address for the instance
            instance_public_ip = create_public_ip_address(logger, client, instance_id)
            if instance_public_ip is None:
                return None

            logger.info('Instance is running - waiting 30 seconds for boot up...')
            time.sleep(30)

            ec2_dict = dict()
            ec2_dict["name"] = instance_dict["name"]
            ec2_dict["id"] = instance_id
            ec2_dict["private_ip"] = instance_private_ip
            ec2_dict["public_ip"] = instance_public_ip
            ec2_dict["vpc_id"] = vpc_id
            ec2_dict["subnet_id"] = subnet_id
            ec2_dict["security_groups"] = sg_dicts
            # add random user passwords for admin and readonly users (mostly useful for Postgres)
            ec2_dict["admin_password"] = sshutils.create_random_password()
            ec2_dict["readonly_password"] = sshutils.create_random_password()
            ec2_dicts.append(ec2_dict)

        return ec2_dicts


def create_security_groups(logger, client, instance_dicts, vpc_id, ipv4_cidr):

    # output dictioanry of security group info
    sg_dicts = list()

    #  get list of security groups to create
    sg_names = list()

    for instance_dict in instance_dicts:
        for sg in instance_dict["security_groups"]:
            sg_name = sg["name"]

            if sg["name"] not in sg_names:
                sg_names.append(sg_name)

                sg_port = sg["port"]
        
                # get CIDR IP range
                if sg["type"] == "public":
                    sg_cidrip = instance_dict["external_ip"]
                else:
                    sg_cidrip = ipv4_cidr

                # create security group(s)
                try:
                    response_dict = client.create_security_group(GroupName=sg_name, Description=sg_name, VpcId=vpc_id)
                    sg_id = response_dict['GroupId']

                    client.authorize_security_group_ingress(
                        GroupId=sg_id,
                        IpPermissions=[
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': sg_port,
                                'ToPort': sg_port,
                                'IpRanges': [{'CidrIp': sg_cidrip}]
                            }
                        ])
                    logger.info("Security group {0} ({1}) created in VPC {2}"
                                .format(sg_name, sg_id, vpc_id))

                    sg_dict = dict()
                    sg_dict["name"] = sg_name
                    sg_dict["id"] = sg_id
                    sg_dict["type"] = sg["type"]
                    sg_dict["port"] = sg_port
                    sg_dict["cidrip"] = sg_cidrip
                    sg_dicts.append(sg_dict)

                except Exception as ex:
                    logger.fatal("Couldn't create security group {0}: {1}".format(sg_name, ex))
                    return None

    return sg_dicts


def create_public_ip_address(logger, client, instance_id):
    try:
        allocation_dict = client.allocate_address(Domain='vpc')
        client.associate_address(AllocationId=allocation_dict['AllocationId'], InstanceId=instance_id)

        ip = allocation_dict["PublicIp"]
        logger.info("Public IP address for {0} is {1}".format(instance_id, ip))

        return ip

    except Exception as ex:
        logger.fatal("Couldn't create public IP address for {0} : {1}".format(instance_id, ex))
        return None


# setup awscli tools on instance for access to other AWS resources (e.g. copy files securely from S3 to EC2)
def install_awscli_tools(logger, ssh_client):
    # get AWS credentials (required to copy pg_dump files from S3)
    from pathlib import Path
    home = str(Path.home())
    cred_array = open(home + "/.aws/credentials", 'r').read().split("\n")

    # create credentials file
    sshutils.run_command(logger, ssh_client, "sudo mkdir ~/.aws/")

    # add credentials to file
    for line in cred_array:
        # write line to file (note: can't echo to a file as su)
        sshutils.run_command(logger, ssh_client, "echo '{}' >> ~/credentials".format(line))

    # copy file to correct directory (to overcome file permissions issue with echo)
    sshutils.run_command(logger, ssh_client, "sudo cp ~/credentials ~/.aws/")

    # install awscli tools
    sshutils.run_command(logger, ssh_client,
                         "sudo DEBIAN_FRONTEND=noninteractive apt -q -y install python3-pip python3-dev")
    sshutils.run_command(logger, ssh_client, "sudo -H pip3 install --upgrade pip")
    sshutils.run_command(logger, ssh_client, "sudo -H pip install awscli")

    return True


def copy_file_to_s3(file, bucket, key):
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file(file, bucket, key)
