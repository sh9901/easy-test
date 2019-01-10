import sys
import json
import pprint
from easy.utils import jsonUtil
import logging


class ModelBase(object):
    def json(self, remove_none=True, remove_tmp_field=True):
        if remove_none and remove_tmp_field:
            return json.loads(self.__repr__(), object_hook=lambda x: {k: v for k, v in x.items() if (v is not None and not k.endswith('__'))})
        elif remove_none and not remove_tmp_field:
            return json.loads(self.__repr__(), object_hook=lambda x: {k: v for k, v in x.items() if v is not None})
        elif not remove_none and remove_tmp_field:
            return json.loads(self.__repr__(), object_hook=lambda x: {k: v for k, v in x.items() if not k.endswith('__')})
        else:
            return json.loads(self.__repr__())

    def str(self):
        return self.__repr__()

    def __repr__(self):
        return json.dumps(self, ensure_ascii=False, sort_keys=True, default=lambda obj: obj.__dict__)

    def __str__(self):
        return self.__repr__()

    def mixin_body(self, key='paramData', dict_stub=None, **kwargs):
        """
        把当前dto转成json拼进stub_dict模板，或者kwargs->dict模板
        :rtype:ModelBase
        :param key:
        :param dict_stub:
        :param kwargs:
        :return:
        """
        if dict_stub:
            dict_stub[key] = self.json()
            return dict_stub
        else:
            param_body = dict(kwargs)
            param_body[key] = self.json()
            return param_body

    @staticmethod
    def to_model(json_content):
        model = ModelBase()
        model.__dict__.update(json_content)
        return model

    def __eq__(self, other) -> bool:
        assert isinstance(other, ModelBase), 'Only support ModelBase instance comparing, real type:%s' % type(other)
        self_dict = self.__dict__
        other_dict = other.__dict__
        if other_dict == self_dict:
            logging.info('Model compare identically match for [self]:\n%s\n- - -against- - -[other]- - -:\n%s\n' % (pprint.pformat(self_dict), pprint.pformat(other_dict)))
            return True
        else:  # __eq__执行严格比对, 如需放宽比对条件可以转为json直接调用jsonUtil.compare
            if jsonUtil.compare(self_dict, other_dict, contains_as_true=False, ignore_none=False, match_type=jsonUtil.MatchType.ExactMatch, unify_name=False, user_defined_match_func=None):
                logging.info('Model COMPARE MATCH\n=>FOR[self.__dict__]=>\n%s\n==>VS[self.__dict__]=>\n%s\n' % (pprint.pformat(self_dict, width=sys.maxsize), pprint.pformat(other_dict, width=sys.maxsize)))
                return True
            else:
                logging.error("Model COMPARE NOT MATCH\n=>FOR[self.__dict__]=>\n%s\n==>VS[other.__dict__]=>\n%s\n" % (pprint.pformat(self_dict, width=sys.maxsize), pprint.pformat(other_dict, width=sys.maxsize)))
                return False
