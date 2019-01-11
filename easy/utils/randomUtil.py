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


def random_int(start: int = None, end: int = None, length: int = None, prefix: int = None) -> int:
    """
    start/end 提供时返回randint(start, end)
    len提供时返回长度为len的整数
    len/prefix提供时返回prefix开头,len长度的整数,如果prefix长度超过则返回prefix

    :param start:
    :param end:
    :param length:
    :param prefix:
    :return:
    """
    if start is not None and end is not None:
        return random.randint(start, end)
    elif length is not None:
        if length < 0:
            raise Exception('len must be a positive number when provided')
        if prefix is None:
            start = int('1' + '0' * (length - 1))
            end = int('9' * length)
            return random.randint(start, end)
        else:
            prelen = len(str(prefix))
            if prelen >= length:
                return prefix
            else:
                length = length - prelen
                start = int('1' + '0' * (length - 1))
                end = int('9' * length)
                return int(str(prefix) + str(random.randint(start, end)))
    else:
        raise Exception('start/end or len[prefix] is required for ramdom_int')
