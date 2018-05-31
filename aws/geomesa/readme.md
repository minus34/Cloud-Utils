



You'll need to have already setup an EC2 key pair as well as the EMR_Default and EMR_EC2_Default roles

Using the AWS Console - create an EMR instance
 - Use the Quick Options
 - Choose the emr-5.12.1 release
 - Select Spark as the application
 - Leave the number of instances at 3 (unless you want to pay more and run it a bit faster)
 - Select your key pair
 - Create the cluster

Wait a few minutes for the cluster to start, while you're waiting get the public IP address of the Master server.

You'll also need to allow SSH access (port 22) from your machine to the Master server. You can set this by editing the the EC2 security group

When the master and core servers are running

run run.sh
