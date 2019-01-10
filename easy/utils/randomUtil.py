import string
import random


def random_str(length, prefix='', type=None):
    '''
    generate random string from letters and digit
    :param int length
    '''
    prefix = str(prefix)
    if length <= len(prefix): return prefix
    length = length - len(prefix)

    if str(type).lower() == 's':
        asciiString = string.ascii_letters
    elif str(type).lower() == 'd':
        asciiString = string.digits
    else:
        asciiString = string.ascii_letters + string.digits

    asciiLen = len(asciiString)
    randomString = ''

    if length <= asciiLen:
        randomString = randomString.join(random.sample(asciiString, length))
    else:
        count = length / asciiLen
        remainder = length % asciiLen

        randomString = randomString.join(random.sample(asciiString, remainder))
        while count > 0:
            randomString = randomString + ''.join(random.sample(asciiString, asciiLen))
            count = count - 1

    return prefix + randomString


def random_int(s: int, b: int) -> int:
    return random.randint(s, b)
