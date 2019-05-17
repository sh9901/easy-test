import re
import json
import logging
import warnings
import urllib.parse
import requests
from collections.abc import Iterable, Sized
from copy import deepcopy
from requests.models import Response
from easy.base.model_base import ModelBase
from . import service_hooks
from pytest_salt import case

absolute_http_url_regexp = re.compile(r"^https?://", re.I)


def valid_hook_funcs(hook_funcs: Iterable = ()):
    assert isinstance(hook_funcs, Iterable), 'hook_funcs must be Iterable'
    for hook_func in hook_funcs:
        assert isinstance(hook_func, Iterable) and isinstance(hook_func, Sized) and len(hook_func) > 0, \
            'hook funcs must be Iterable with Iterable children, ' \
            'and children have func name at least, ' \
            'hook func args are optional, ' \
            'such as ([func1,arg1,arg2],(func2,),[func3])'


class ServiceBase(object):
    def __init__(self, host, vpath='', hook_funcs: Iterable = (), headers: dict = None, cookies: dict = None):
        valid_hook_funcs(hook_funcs)
        self.host = host
        self.vpath = vpath
        self.hook_funcs = hook_funcs
        self.hook_funcs = list(self.hook_funcs) if self.hook_funcs else []
        self.headers = headers
        self.cookies = cookies

        # 通用hooks-default enalbed
        self.hook_funcs.append([service_hooks.ensure_utf8_g])
        self.hook_funcs.append([service_hooks.check_response_in_time_g, 10])
        self.hook_funcs.append([service_hooks.print_response_info_g])

        # Only suitable for positives.disable by default
        # self.hook_funcs.append([service_base_hooks.check_http_code_g, 200])
        # self.hook_funcs.append([service_base_hooks.check_status_code, 0])

    # region before request/ after response 等增强特性

    def __before_request(self, method, url, **kwargs):

        if 'info' in kwargs:
            if kwargs.get('info'):
                logging.info(kwargs.pop('info'))
            else:
                kwargs.pop('info')

        logging.info('Request.Method: %s' % method)
        logging.info('Request.URL:  : %s' % url)

        # requests中独立参数,以(params<data/json>, **kwargs)传入时获取到的kwargs值会被污染,去掉,且不需要返回
        if 'params' in kwargs:
            if kwargs.get('params'):
                logging.info('Request.params: %s' % kwargs.pop('params'))
            else:
                kwargs.pop('params')

        if 'data' in kwargs:
            if kwargs.get('data'):
                logging.info('Request.data  : %s' % kwargs.pop('data'))
            else:
                kwargs.pop('data')

        if 'json' in kwargs:
            if kwargs.get('json'):
                logging.info('Request.json  : %s' % kwargs.pop('json'))  # json or extracted from model load
            else:
                kwargs.pop('json')

        if not kwargs.get('headers'):
            kwargs['headers'] = self.headers

        if not kwargs.get('cookies'):
            kwargs['cookies'] = self.cookies

        # files不作为requests独立参数使用,不会造成kwargs污染,不需要去掉<要遵守requests标准用法>
        logging.info('Request.files : %s' % kwargs['files']) if kwargs.get('files') else None

        # servicebase扩展的参数,不实际参加requests请求,需要从kwargs中取出来,给__after_request使用
        hook_funcs = kwargs.get('hook_funcs')
        hook_funcs = list(kwargs.pop('hook_funcs')) if hook_funcs and isinstance(hook_funcs, Iterable) else []
        # for hook_funcs shortcut,keep both for bdr<defined hooks in lower level using 'hook_funcs', not overrided, noqa.>
        hook_funcs_u = kwargs.get('H')
        hook_funcs_u = list(kwargs.pop('H')) if hook_funcs_u and isinstance(hook_funcs_u, Iterable) else []
        hook_funcs.extend(hook_funcs_u)
        valid_hook_funcs(hook_funcs)

        model_hook = kwargs.pop('model_hook') if kwargs.get('model_hook') else None
        model_hook = kwargs.pop('M') if kwargs.get('M') else model_hook  # for mode_hook shortcut

        if hook_funcs:
            valid_hook_funcs(hook_funcs)

        return hook_funcs, model_hook, kwargs

    def __after_request(self, resp: Response, hook_funcs=(), model_hook=None, **kwargs):
        local_hook_funcs = deepcopy(self.hook_funcs) if True else []  # 留作是否复用默认配置
        local_hook_funcs.extend(hook_funcs)  # 默认配置和自定义配置聚合
        # 1.
        # todo 处理请求记录之类的写入api_log表
        # 请求记录,用例描述等信息运行时写入到case.caseinfo中, session结束后写入db
        case.pack_case_info(resp)

        # 2.尝试给resp加model,即使失败仍要加上model=None属性
        if model_hook == ModelBase.to_model:
            try:
                # set model format object back to response
                setattr(resp, 'model', json.loads(json.dumps(resp.json(), ensure_ascii=False), object_hook=model_hook))
            except Exception as e:
                logging.warning('attach resp content to model attr failed, %s' % e)
                setattr(resp, 'model', None)
        else:
            setattr(resp, 'model', None)  # 没有自定义object_hook则model不取值

        # 3. hook的插入和解除机制<hooks_funcs>
        # 通过最后一个参数ignore/xignore识别给用户一个取消hook（通用配置或controller中配置的）执行的机会
        # 使用ignore时只判断hook方法名标记了就忽略掉
        # 使用xignore时同时判断hook方法名和参数
        ignored_funcs = set()
        for func in local_hook_funcs:
            assert callable(func[0]), 'func:%s is not callable' % func[0].__name__
            if str(func[-1]).lower() == 'ignore':
                ignored_funcs.add((func[0].__name__, None))
            elif str(func[-1]).lower() == 'xignore':
                ignored_funcs.add((func[0].__name__, '|'.join([str(x) for x in func[1:-1]])))

        # 已执行的hook列表，方法名+参数匹配，避免同样的配置重复执行
        hooked_funcs = set()
        try:
            if local_hook_funcs and isinstance(local_hook_funcs, Iterable):
                for func in local_hook_funcs:
                    if (func[0].__name__, None) in ignored_funcs and str(func[-1]).lower() == 'ignore':
                        continue
                    elif (func[0].__name__, None) in ignored_funcs:
                        logging.info('Hook Ignored  : %s::%s with args:[%s] ignored by user.' % (
                            func[0].__module__, func[0].__name__, '|'.join([str(x) for x in func[1:]])))
                        continue
                    elif (func[0].__name__, '|'.join([str(x) for x in func[1:-1]])) in ignored_funcs and str(
                            func[-1]).lower() == 'xignore':
                        continue
                    elif (func[0].__name__, '|'.join([str(x) for x in func[1:-1]])) in ignored_funcs:
                        logging.info('Hook Ignored  : %s::%s with args:[%s] xignored by user.' % (
                            func[0].__module__, func[0].__name__, '|'.join([str(x) for x in func[1:]])))

                    if (func[0].__name__, '|'.join([str(x) for x in func[1:]])) not in hooked_funcs:  # 检查该hook+args是否已经执行过
                        logging.info('Hook Executing: %s::%s with args:[%s]' % (
                            func[0].__module__, func[0].__name__, ','.join([str(x) for x in func[1:]])))
                        func[0](resp, *func[1:])  # 执行hook
                        hooked_funcs.add((func[0].__name__, '|'.join([str(x) for x in func[1:]])))  # hook+str(args)记入执行记录
                    else:
                        logging.info('Hook Skipped  : %s::%s with args:[%s] duplicated, skip.' % (
                            func[0].__module__, func[0].__name__, ','.join([str(x) for x in func[1:]])))
        except Exception as e:
            raise Exception('Hook func [%s::%s] with args:[%s] FAILURE [REASON: %s] of resp:%s',
                            (func[0].__module__, func[0].__name__, ','.join([str(x) for x in func[1:]]), e, resp.text))

        return resp

    # endregion

    # region requests api的简单封装
    # 1. 增加了load参数, 支持传入model对象, 方便外部处理, 传入后反序列化为json
    # 2. 增加了hook_funcs参数, 接收([func, arg1, arg2],)形式的输入, 用于扩展resp的灵活处理
    # 3. 增加了model_hook参数, 用于将requests返回的response上的json()对象序列化为model对象附加在resp上返回调用方, 调用方通过resp.model获取到这个值后可以作为对象类型使用
    # 4. [removed]增加了json_return参数, 作为resp.json()的快捷方式, 强烈不建议使用, 仅为保持旧使用习惯兼容, 建议使用model处理入参和返回
    # 5. 拿掉了request中的hook_funcs/model_hook/json_return[removed]参数,统一从kwargs里传入,目的是防止test/service/controller层重复传入误用,导致
    #    TypeError: get() got multiple values for keyword argument 'hook_funcs',为弥补易输错的麻烦增加入了'H'/'M','J' shortcuts
    #    <方便>与<安全>的tradeoff,controller中仍然可以提供默认的设置,test/service中可以覆盖
    def request(self, method, path_or_url, load: ModelBase = None, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        if load:
            assert isinstance(load, ModelBase), 'load:%s is not subclass of ModelBase' % load
            kwargs['json'] = load.json()
        else:
            kwargs['json'] = kwargs['json'].json() if kwargs['json'] and isinstance(kwargs['json'], ModelBase) else kwargs['json']
        hook_funcs, model_hook, kwargs = self.__before_request(method, path_or_url, **kwargs)
        resp = requests.request(method.lower(), path_or_url, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def get(self, path_or_url, params=None, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        hook_funcs, model_hook, kwargs = self.__before_request('get', path_or_url, params=params, **kwargs)
        resp = requests.get(path_or_url, params, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def options(self, path_or_url, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        hook_funcs, model_hook, kwargs = self.__before_request('option', path_or_url, **kwargs)
        resp = requests.options(path_or_url, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def head(self, path_or_url, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        hook_funcs, model_hook, kwargs = self.__before_request('head', path_or_url, **kwargs)
        resp = requests.head(path_or_url, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def post(self, path_or_url, load=None, data=None, json=None, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        if load:
            assert isinstance(load, ModelBase), 'load:%s is not subclass of ModelBase' % load
            json = load.json()
        else:
            json = json.json() if isinstance(json, ModelBase) else json
        hook_funcs, model_hook, kwargs = self.__before_request('post', path_or_url, data=data, json=json, **kwargs)
        resp = requests.post(path_or_url, data, json, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def put(self, path_or_url, load=None, data=None, json=None, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        if load:
            assert isinstance(load, ModelBase), 'load:%s is not subclass of ModelBase' % load
            json = load.json()
        else:
            json = json.json() if isinstance(json, ModelBase) else json
        hook_funcs, model_hook, kwargs = self.__before_request('put', path_or_url, data=data, json=json, **kwargs)
        resp = requests.put(path_or_url, data, json=json, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def patch(self, path_or_url, load=None, data=None, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        if load:
            assert isinstance(load, ModelBase), 'load:%s is not subclass of ModelBase' % load
            kwargs['json'] = load.json()
        else:
            kwargs['json'] = kwargs['json'].json() if kwargs['json'] and isinstance(kwargs['json'], ModelBase) else kwargs['json']
        hook_funcs, model_hook, kwargs = self.__before_request('patch', data=data, **kwargs)
        resp = requests.patch(path_or_url, data, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    def delete(self, path_or_url, **kwargs) -> Response:
        path_or_url = self.__abs_url(path_or_url)
        hook_funcs, model_hook, kwargs = self.__before_request('delete', path_or_url, **kwargs)
        resp = requests.delete(path_or_url, **kwargs)
        final_resp = self.__after_request(resp, hook_funcs, model_hook, **kwargs)
        return final_resp

    # endregion

    def __abs_url(self, path):
        if absolute_http_url_regexp.match(path):
            return path
        else:
            if self.vpath:
                return self.host.rstrip('/') + self.vpath.rstrip('/') + path
            else:
                return self.host.rstrip('/') + path

    def raise_exception(self, request, response: Response, should_success=True, message=''):
        """
        when a request fail, is it expected or should it raise an exception
        :param request:
        :param response:
        :param should_success:
        :param message:
        :return:
        """
        if should_success:
            raise Exception(
                '%s\n[REQUEST:<%s>]\n[RESPONSE:<%s-%s,%s>]' % (message, request, response.status_code, response.reason, response.text))

    # region 不推荐使用的url辅助方法
    def build_url(self, path, path_param_list=None, query_params: dict = None, ensure_slash=False):
        warnings.warn("强烈不推荐使用，保留仅为兼容旧的使用习惯，推荐使用host/path/params等http标准做法", DeprecationWarning, 2)

        path = self.build_path(path, path_param_list, ensure_slash)
        abs_path = self.__abs_url(path)

        paraValue = self.__encodeUrlParams(query_params, True) if query_params and isinstance(query_params, dict) else ''
        paraStr = ('?' + paraValue) if paraValue else ''

        return abs_path + paraStr

    def build_path(self, path, path_param_list=None, enable_slash=False):
        warnings.warn("强烈不推荐使用，保留仅为兼容旧的使用习惯，推荐使用host/path/params等http标准做法", DeprecationWarning, 2)

        _path = ""
        if path:
            _path = _path.rstrip('/') + path

        if path_param_list:
            more_path = '/'.join(path_param_list)
            _path = _path.rstrip('/') + '/' + more_path

        if enable_slash:
            _path = _path.rstrip('/') + '/'

        return _path

    def __encodeUrlParams(self, params, needencode=True):
        """
        不推荐使用.
        encode request parameters dict to query string, like: param1=value1&param2=value2
        eg: {"param1": "value1", "param2": None, "param3": ""} => param1=value1&param3=
        :param params: dict, request query parameters.
        :return string, like "param1=&param3=value3"
        """
        warnings.warn("强烈不推荐使用，保留仅为兼容旧的使用习惯，推荐使用host/path/params等http标准做法", DeprecationWarning, 2)
        if params is not None:
            for (key, value) in list(params.items()):
                if value is None:
                    params.pop(key)

            if len(params) > 0:
                if not needencode:
                    params_str_list = []
                    for (key, value) in list(params.items()):
                        params_str_list.append(key + "=" + str(value))
                    return '&'.join(params_str_list)
                return urllib.parse.urlencode(params)
        return ''

    # endregion
