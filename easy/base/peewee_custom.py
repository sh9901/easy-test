from peewee import BooleanField


class BitBooleanField(BooleanField):
    field_type = 'bit'

    def db_value(self, value):
        if value:
            return b'\x01'
        else:
            return b'\x00'

    def python_value(self, value):
        if value == b'\x01':
            return True
        elif value == b'\x00':
            return False
        else:
            raise Exception('cannot convert {0} from mysql db field to python field')
