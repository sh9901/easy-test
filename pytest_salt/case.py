import os
import sys
import inspect
from urllib.parse import urlparse
from requests.models import Response
from . import salt


def pack_case_info(resp: Response):
    """通过inspect获取testmethod的信息,name,module,doc描述,sourcecode"""
    # frame for test method, noqa
    stacks_test = filter(lambda x: x.function.startswith('test') and os.path.split(x.filename)[-1].startswith('test'),
                         [p for p in inspect.stack()])
    for stack in stacks_test:
        case_name = stack.function
        case_file = stack.filename
        frame = stack.frame
        # f_locals = frame.f_locals
        case_class = type(frame.f_locals['self']).__name__ if 'self' in frame.f_locals else ''
        case_doc = __get_case_doc(inspect.getsource(frame))

        url_parse = urlparse(resp.request.url)

        case_api = {
            'method': resp.request.method,
            'host': url_parse.hostname,
            'path': url_parse.path,
            'query': url_parse.query,
            'headers': '%s' % resp.request.headers,
            # 'request_body': '%s' % resp.request.body,
            'status_code': resp.status_code,
            'elapsed': resp.elapsed.total_seconds(),
            'response_body': '%s' % resp.text,
            'nodeid': None  # 搜集api信息时无法获取nodeid信息,可以之后由pytest_report_teststatus补充进去
        }

        paths = sys.path
        for path in paths:
            if path in case_file:  # guess a valid path to trim extras prefix for module value, noqa
                case_file = '/'.join(case_file.split(os.sep))
                case_unique = '%s::%s::%s' % (case_file, case_class, case_name)

                case_module = case_file[len(path):]
                case_module = '.'.join(case_module.split(os.path.sep)).lstrip('.')

                if not case_unique in salt.caseinfo:
                    salt.caseinfo[case_unique] = {
                        'case_module': case_module,
                        'case_class': case_class,
                        'case_name': case_name,
                        'case_doc': case_doc,
                        'case_apis': [case_api]
                    }
                else:
                    salt.caseinfo[case_unique]['case_apis'].append(case_api)

                break  # more than one path will match, take the first one, break required.


def __get_case_doc(case_source):
    t_count = case_source.count('"""')
    case_doc_list = []
    if t_count > 0:
        p1 = case_source.find('"""')
        p2 = case_source.find('"""', p1 + 1)

        if p2 == p1 + 1:
            return ''

        docs = case_source[p1:p2].split('\n')

        for doc_line in docs:
            doc_line = doc_line.strip()
            if doc_line in ('', '"""', '""""""'):
                continue
            elif doc_line.startswith(':'):  # ignore :rtype :param etc.. noqa
                continue
            elif doc_line.startswith('"""'):
                case_doc_list.append(doc_line[3:])
            elif doc_line.endswith('"""'):
                case_doc_list.append(doc_line[:-3])
            else:
                case_doc_list.append(doc_line)
    case_doc = ','.join(case_doc_list)
    return case_doc
