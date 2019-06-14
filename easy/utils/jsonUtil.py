import json
import pprint
import logging
import re
import sys
import jsondiff
from requests.models import Response
from datetime import date, datetime
from easy.utils import dateUtil


def pprint_json(json_dict: dict):
    """print pretty josn string, 打印版优化"""
    logging.info('+' * 40)
    logging.info('\n%s' % pprint.pformat(json_dict, indent=2))
    logging.info('+' * 40)


def print_json(json_dict: dict):
    """阅读版优化"""
    logging.info('+' * 40)
    logging.info('\n%s' % json.dumps(json_dict, ensure_ascii=False, indent=2, sort_keys=True))
    logging.info('+' * 40)


def pformat_json(json_dict: dict) -> str:
    return json.dumps(json_dict, indent=2, ensure_ascii=False, sort_keys=True)


def pformat_resp(resp: Response) -> str:  # noqa
    """
    for print purpose, result could be truncated when to large(gt 256KByte)
    :param resp: Response
    :return: json like string
    """
    try:
        resp_length = len(resp.text)
        if resp_length <= 2 ** 18:
            # json_string = json.dumps(resp.json(), indent=2, ensure_ascii=False, sort_keys=True)
            # elif 2 ** 10 < resp_length <= 2 ** 18:
            json_string = json.dumps(resp.json(), ensure_ascii=False, sort_keys=True)
        else:
            json_string = 'RESPONSE CONTENT TOO LONG TO DISPLAY, FOR SHORT(256 KByte): %s' % json.dumps(resp.json(), ensure_ascii=False, sort_keys=True)[:2 ** 18]
        return json_string
    except Exception as e:
        logging.error('Try json format response exception:%s, use resp.text instead' % e)
        return resp.text


class Defaults(object):
    """用于json.dumps default参数 """

    def __init__(self, dt_fmt=dateUtil.FMT.TIME_T_TZ):
        self.dt_fmt = dt_fmt

    def date_default(self, value):
        if isinstance(value, (date, datetime)):
            return value.strftime(self.dt_fmt)


class MatchType:
    RegexMatch = 0
    ExactMatch = 1


class CompareSettings(object):
    def __init__(self, ignore_none=False, unify_name=False, match_type=MatchType.ExactMatch, contains_as_true=True, user_defined_match_func=None):
        self.ignore_none = ignore_none
        self.unify_name = unify_name
        self.match_type = match_type
        self.contains_as_true = contains_as_true
        self.user_defined_match_func = user_defined_match_func

    def json(self):
        return self.__dict__
        # return json.loads(json.dumps(self, ensure_ascii=False, sort_keys=True, default=lambda obj: obj.__dict__))


def compare_object(actual_obj, expect_obj, contains_as_true=True, ignore_none=True, match_type=MatchType.ExactMatch, unify_name=False, user_defined_match_func=None) -> bool:
    """
    dict或支持通过json()获取dict的object比对, 调用jsonUti.compare()
    :param actual_obj: dict or object has json() attr
    :param expect_obj: dict or object has json() attr
    :param contains_as_true:
    :param ignore_none:
    :param match_type:
    :param unify_name:
    :param user_defined_match_func:
    :return: bool
    """
    actual_obj = actual_obj if isinstance(actual_obj, dict) else (actual_obj.json() if hasattr(actual_obj, 'json') else None)
    expect_obj = expect_obj if isinstance(expect_obj, dict) else (expect_obj.json() if hasattr(expect_obj, 'json') else None)
    assert isinstance(actual_obj, dict) and isinstance(expect_obj, dict), 'actual_obj/expect_obj must be dict or has obj.json()'
    return compare(actual_obj, expect_obj, contains_as_true, ignore_none, match_type, unify_name, user_defined_match_func)


def compare(actual: dict, expect: dict, contains_as_true=True, ignore_none=True, match_type=MatchType.ExactMatch, unify_name=False, user_defined_match_func=None) -> bool:
    """
    json/dict比对
    :param actual:
    :param expect:
    :param ignore_none:
    :param unify_name:     if unify_name:  # 为了解决crm_sale_id和crmSaleId无法匹配的问题, 统一处理为CRMSALEID
    :param match_type: MatchType(RegexMatch/ExactMatch)枚举,传入1,True等可判为True的字段都作为ExactMatch处理,其它如0,FALSE则作为RegexMatch,,枚举类型保留扩展
    :param contains_as_true: 期望值包含于实际值则认为匹配, 用于支持仅比对部分字段
    :param user_defined_match_func: 提供给用户自定义比较方式的插入点, 如果提供则只根据参数处理ignore_none/unify_name, 而不执行内置的比对逻辑,该方法期望返回bool型结果
    :return: bool
    """
    assert isinstance(actual, dict) and isinstance(expect, dict), 'only support json compare, actual %s vs %s' % (actual, expect)

    if ignore_none:
        actual = __remove_none(actual)
        expect = __remove_none(expect)

    if unify_name:  # 为了解决crm_sale_id和crmSaleId无法匹配的问题
        actual = __full_up_case(actual)
        expect = __full_up_case(expect)

    if user_defined_match_func and callable(match_type):  # 如果提供用户自定义比对方法则执行, 且跳过内置比对逻辑
        return user_defined_match_func(**locals())
    else:
        if match_type:  # 精确匹配
            diff_result = jsondiff.diff(actual, expect)
            if diff_result:  # 有匹配不一致内容, 需要进一步判断
                if contains_as_true:  # 全字段精确匹配未通过, 去掉diff返回结果中key为delete的看是否满足包含匹配,因为expect没有提供完整结构导致
                    diff_result = __ignore_missed_field(diff_result)  # 如果匹配应该返回{}
                    if not bool(diff_result):  # 部分精确匹配通过
                        logging.info('JSON PARTIAL EXACT MATCH, Result: PASS, Detail:\n>>>>>ACTUAL>>>>>\n%s\n>>>>>EXPECT>>>>>\n%s' %
                                     (pprint.pformat(actual, width=sys.maxsize),
                                      pprint.pformat(expect, width=sys.maxsize)))
                        return True
                    else:
                        logging.error('JSON PARTIAL EXACT MATCH, Result: FAIL, Detail:\n>>>>>MISSED>>>>>\n%s\n>>>>>ACTUAL>>>>>\n%s\n>>>>>EXPECT>>>>>\n%s' %
                                      (pprint.pformat(diff_result, indent=2),
                                       pprint.pformat(actual, width=sys.maxsize),
                                       pprint.pformat(expect, width=sys.maxsize)))
                        return False
                else:  # 未全字段精确匹配, 也没有包含匹配, 期望中值有变动或新增
                    logging.error('JSON FULL EXACT MATCH, Result: FAIL, Detail:\n%s\n>>>>>ACTUAL>>>>>\n%s\n>>>>>EXPECT>>>>>\n%s' %
                                  (pprint.pformat(diff_result, indent=2),
                                   pprint.pformat(actual, width=sys.maxsize),
                                   pprint.pformat(expect, width=sys.maxsize)))
                    return False
            else:  # 全字段精确匹配, diff返回为{}即为匹配
                logging.info('JSON FULL EXACT MATCH, Result: PASS, Detail:\n>>>>>ACTUAL>>>>>\n%s\n>>>>>EXPECT>>>>>\n%s' %
                             (pprint.pformat(actual, width=sys.maxsize),
                              pprint.pformat(expect, width=sys.maxsize)))
                return True
        else:  # 非精确匹配, 暂时只支持正则匹配
            match_name = 'JSON PARTIAL REGEX MATCH' if contains_as_true else 'JSON FULL REGEX MATCH'  # pitfall
            match, match_info = regex_compare(actual, expect, contains_as_true, match=True, match_info='Match OK.', ori_actual=actual, ori_expected=expect)
            if match:
                compare_content = "%s:\n>>>>>ACTUAL>>>>>\n%s\n>>>>>EXPECT>>>>> \n%s" % (match_name, pprint.pformat(actual, width=sys.maxsize), pprint.pformat(expect, width=sys.maxsize))
                logging.info(compare_content)
                logging.info(match_info)
                return True
            else:
                # logging.error(compare_content) # 失败时返回match_info包含全部信息
                logging.error(match_info)
                return False


def __remove_none(data: dict):
    """抛弃dict.value为空的item, 以及value为list时该list中的None值"""
    if isinstance(data, list):
        for x in range(len(data) - 1, 0, -1):
            if data[x] is None:
                del data[x]
            else:
                __remove_none(data[x])
    elif isinstance(data, dict):
        keys = list(data.keys())
        for key in keys:
            if data[key] is None or key.endswith('__'):  # ignore user temporarily added xx__ fields as None
                data.pop(key)
            elif isinstance(data[key], dict):
                __remove_none(data[key])
            elif isinstance(data[key], list):
                for lv in data[key]:
                    __remove_none(lv)
            else:
                pass
    else:  # 基础类型不需处理
        pass

    return data


def __full_up_case(data: dict):
    """dict key值变为全大写并去掉下划线, 如:crm_sales_id -> CRMSALEID"""
    if isinstance(data, list):
        for lv in data:
            __full_up_case(lv)
    elif isinstance(data, dict):
        keys = list(data.keys())
        for key in keys:
            new_key = key.replace('_', '').upper()
            value = data.pop(key)
            data[new_key] = value
            if isinstance(value, dict):
                __full_up_case(value)
            elif isinstance(value, list):
                for lv in value:
                    __full_up_case(lv)
            else:
                pass
    else:  # 基础类型保持不变, 可能来源于item.list[n]
        pass

    return data


def __ignore_missed_field(diff_result: dict):
    """去掉diff_result中key未delete的item, 这种字段是期望中没有提供导致的, dict之外还需要支持list(不需要考虑tuple/set等,因为json不支持)入参, 因为递归中可以能会遇到item值为此类型"""
    if isinstance(diff_result, list):
        for lv in diff_result:
            __ignore_missed_field(lv)
    elif isinstance(diff_result, dict):
        keys = list(diff_result.keys())
        for key in keys:
            if isinstance(key, jsondiff.Symbol) and key.label == 'delete':
                diff_result.pop(key)
            elif isinstance(diff_result[key], dict):
                __ignore_missed_field(diff_result[key])
            elif isinstance(diff_result[key], (list)):
                for lv in diff_result[key]:
                    __ignore_missed_field(lv)
            else:
                pass
    else:  # 基础类型不需处理
        pass

    if isinstance(diff_result, dict):
        keys = list(diff_result.keys())
        for key in keys:
            if diff_result[key] == {}:
                diff_result.pop(key)

    return diff_result


ORIGI_HOLDER = '\n[<%s>]'


def regex_compare(actual: dict, expect: dict, contains_as_ture=True, match=True, match_info='MATCH OK.', ori_actual=None, ori_expected=None):
    if not match:
        return False, match_info
    if type(actual) != type(expect):
        return False, 'JSON REGEX MATCH RESULT:FAIL,Reason:args type not match\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECTED>>>>>\n%s%s' \
               % (pprint.pformat(actual, width=sys.maxsize),
                  ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                  pprint.pformat(expect, width=sys.maxsize),
                  ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')
    if not isinstance(actual, (dict, list)) or not isinstance(expect, (dict, list)):
        return False, "JSON REGEX MATCH RESULT:FAIL,Reason:only support dict/list\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s" \
               % (pprint.pformat(actual, width=sys.maxsize),
                  ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                  pprint.pformat(expect, width=sys.maxsize),
                  ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')

    if isinstance(expect, list):  # 则都为list
        if len(actual) == len(expect) == 0:
            return True, 'JSON REGEX MATCH RESULT:PASS,Reason:LIST CONTENT IS EMPTY.'
        elif len(actual) == 0 or len(expect) == 0:
            return False, 'JSON REGEX MATCH RESULT:FAIL,Reason:ACTUAL OR EXPECTED JSON LIST IS EMPTY\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s' \
                          % (pprint.pformat(actual, width=sys.maxsize),
                             ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                             pprint.pformat(expect, width=sys.maxsize),
                             ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize)) if expect != ori_expected else ''
        else:
            lve = expect[0]
            for lva in actual:
                match, match_info = regex_compare(lva, lve, contains_as_ture, match, match_info, ori_expected, ori_expected)
                if not match:
                    return match, match_info
    elif isinstance(expect, dict):  # 则都为dict
        keyas = sorted(actual.keys())
        keys = keyes = sorted(expect.keys())
        if contains_as_ture:
            key_missed = False in [k in keyas for k in keyes]
        else:
            key_missed = False in [ka in keyes for ka in keyas] or False in [ke in keyas for ke in keyes]

        if key_missed:
            return False, 'JSON REGEX MATCH RESULT:FAIL,Reason:KEYS MISSED\nACTKEYS:%s\nEXPKEYS:%s\nNOT MATCH FOR:\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s' \
                   % (pprint.pformat(keyas, width=sys.maxsize),
                      pprint.pformat(keyes, width=sys.maxsize),
                      pprint.pformat(actual, width=sys.maxsize),
                      ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                      pprint.pformat(expect, width=sys.maxsize),
                      ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')
        else:
            for key in keys:
                if expect[key] in ('*', '.*'):
                    continue
                elif isinstance(expect[key], dict):
                    if isinstance(actual[key], dict):
                        match, match_info = regex_compare(actual[key], expect[key], contains_as_ture, match, match_info, ori_actual, ori_expected)
                        if not match:
                            return match, match_info
                    else:
                        return False, "JSON REGEX MATCH RESULT:FAIL,Reason:object[%s] TYPE ERROR:\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s" \
                               % (key,
                                  pprint.pformat(actual, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                                  pprint.pformat(expect, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')
                elif isinstance(expect[key], list):
                    if isinstance(actual[key], list):
                        llvve = expect[key][0]
                        for llvva in actual[key]:
                            match, match_info = regex_compare(llvva, llvve, contains_as_ture, match, match_info, ori_actual, ori_expected)
                            if not match:
                                return match, match_info
                    else:
                        return False, "JSON REGEX MATCH RESULT:FAIL,Reason:object[%s] TYPE ERROR:\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s" \
                               % (key,
                                  pprint.pformat(actual, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                                  pprint.pformat(expect, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')
                else:  # primitive value
                    if not re.match(str(expect[key]), str(actual[key])):
                        return False, 'JSON REGEX MATCH RESULT:FAIL,Reason:[%s:%s] NOT MATCH PATTERN [%s:%s]:\n>>>>>ACTUAL>>>>>\n%s%s\n>>>>>EXPECT>>>>>\n%s%s' \
                               % (key,
                                  pprint.pformat(actual[key], width=sys.maxsize),
                                  key,
                                  pprint.pformat(expect[key], width=sys.maxsize),
                                  pprint.pformat(actual, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_actual, width=sys.maxsize) if actual != ori_actual else '',
                                  pprint.pformat(expect, width=sys.maxsize),
                                  ORIGI_HOLDER % pprint.pformat(ori_expected, width=sys.maxsize) if expect != ori_expected else '')

    return match, match_info
