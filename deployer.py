
import argparse
import ast
import logging
import os

logging.getLogger("paramiko").setLevel(logging.INFO)


def main():
    # get config file argument
    parser = argparse.ArgumentParser(description='Builds one or more server instance on your cloud provider of choice.')
    parser.add_argument('--config', help='JSON file containing your config settings')
    args = parser.parse_args()

    # get config file path
    config_path = args.config or os.path.dirname(os.path.realpath(__file__)) + os.sep + "sample_settings"\
        + os.sep + "ec2.json"

    # load config into setting dictionary
    file = open(config_path, "r").read()
    settings = ast.literal_eval(file)

    # get proxy settings from passwords.ini file
    if "proxy" in settings:
        proxy = settings["proxy"]
    else:
        proxy = None

    # create instances
    if settings["provider"] == "aws":
        from aws import awsdeploy
        result = awsdeploy.build_servers(settings, logger, proxy)
    # elif settings["provider"] == "azure":
    #     from azure import azuredeploy
    #     # Do Azure stuff
    else:
        logger.fatal("Only AWS deployments supported at this time")
        result = False

    return result


if __name__ == '__main__':
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
    logger.info("Start server deployment")

    if main():
        logger.info("Finished successfully!")
    else:
        logger.fatal("Something bad happened!")

    logger.info("")
    logger.info("-------------------------------------------------------------------------------")
