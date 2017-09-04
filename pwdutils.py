#
# password utilities
#

import string
import random


def create_random_password():
    password_size = random.randint(0, 10) + 40
    chars = string.ascii_letters + string.digits
    password = ''.join((random.choice(chars)) for x in range(password_size))

    return password
