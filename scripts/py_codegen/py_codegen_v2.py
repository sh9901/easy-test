import sys
import os
import re
import shutil
import argparse
import json
import time
import requests
import autopep8
from collections import namedtuple
from typing import List
from datetime import datetime
import tempfile

sp = " "
sp4 = sp * 4
sp8 = sp * 8
sp12 = sp * 12
sp16 = sp * 16

Model = namedtuple('model', ['model_file', 'model_class'])
Path = namedtuple('path', ['path_file', 'path_class'])

outbox_setup = """from setuptools import setup, find_packages

setup(name="{{APP_NAME}}",
      version='{{APP_VERSION}}',
      description='{{APP_NAME}}@{{APP_VERSION}} API bridge with controller/model',
      author='YangHuawei',
      author_email='yanghuawei@hujiang.com',
      url='http://qa.yeshj.com',
      packages=find_packages(),
      keywords='requests api test easy pytest plugin',
      install_requires=['pytest>=4.0',
                        'requests',
                        'ease-test'
                        ],
      classifiers=[
          'Development Status :: Production/Stable',
          'Intended Audience :: QA Engineers / Developers',
          'Operating System :: Linux',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: MacOS :: MacOS X',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Software Development :: Testing',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
      ])
"""


def swagger_type_to_python(swagger_type, format=None):
    if swagger_type == 'integer':
        return 'int'
    elif swagger_type == 'number':
        return 'float'
    elif swagger_type == 'string':
        if format == 'date-time':
            return '"str [datetime]"'
        else:
            return 'str'
    elif swagger_type == 'boolean':
        return 'bool'
    elif swagger_type == 'date-time':
        return '"str [datetime]"'
    else:
        return 'object'


def camel_case_to_under_score(camel_case):
    return ''.join(map(lambda x: x if (x.islower() or x == '_' or str(x).isdigit()) else '_' + x.lower(), camel_case)).lstrip('_')


def wrap_line(line, max_len=140):
    if len(line) < max_len:
        return line

    start = sp * (line.lstrip('\n').find('('))
    sections = line.split(',')

    wrapped_line = ''
    current_line = ''
    is_first_row = True
    for section in sections:
        if is_first_row:
            try_len = len(current_line + section)
            if try_len < max_len:
                current_line += section + ','
            else:
                wrapped_line += current_line + '\n'
                current_line = ''
                current_line += start + section + ','
                is_first_row = False
        else:
            current_line = start + current_line if not current_line.startswith(start) else current_line
            try_len = len(current_line + section)
            if try_len < max_len:
                current_line += section + ','
            else:
                wrapped_line += current_line + '\n'
                current_line = ''
                current_line = start + current_line if not current_line.startswith(start) else current_line
                current_line += section + ','

    if current_line:
        wrapped_line += current_line

    return wrapped_line.rstrip(',')


def wrap_params():
    pass


class PyCodeGen(object):

    def __init__(self, args):
        self.swagger_doc = args.swagger_doc
        self.api_bases = args.api_bases
        self.code_base = args.code_base
        self.controller_base = args.controller_base
        self.service_base = args.service_base
        self.model_base = args.model_base
        self.included_paths = args.included_paths
        self.excluded_paths = args.excluded_paths
        self.target_relative_dir = args.target_relative_dir

        self.out_box = args.out_box
        self.app_where = args.app_where
        self.app_name = args.app_name
        self.app_version = args.app_version
        self.pip_name = args.pip_name

        if not self.out_box:
            if self.swagger_doc and self.code_base:
                if self.target_relative_dir:
                    try:
                        os.chdir(self.target_relative_dir)
                    except:
                        print('切换当前目录到%s失败' % self.target_relative_dir)
                        sys.exit(-1)
                # 如果代码目录、swagger doc地址已获取，则初始化项目目录结构
                self.init_base_dir(args.keep)
            else:
                print('swagger_doc没有提供且没有自动获取到，退出处理')
                sys.exit(-1)
        else:
            with tempfile.TemporaryDirectory(prefix='autoapi') as tmpdir:
                os.chdir(tmpdir)
                os.mkdir(self.app_name)
                os.chdir(self.app_name)
                app_folder = self.app_name.replace('-', '_')
                setup = outbox_setup.replace('{{APP_NAME}}', self.app_name).replace('{{APP_VERSION}}', self.app_version)
                with open('setup.py', 'w') as f:
                    f.write(setup)
                os.mkdir(app_folder)
                os.chdir(app_folder)
                self.init_base_dir(keep=False)
                self.run()
                os.chdir('../')
                os.system('%s wheel . -w %s' % (self.pip_name, os.path.expanduser(self.app_where)))

    def init_base_dir(self, keep):
        if keep:  # 如果保留老版本则先备份
            backups = ".backups"
            backupstamp = '%Y%m%d%H%M%S_'
            if not os.path.exists(backups):
                os.mkdir(backups)
            if os.path.exists(self.controller_base):
                controoler_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.controller_base)))
                controller_backup = os.path.join(backups, controoler_ctime + self.controller_base)
                shutil.move(self.controller_base, controller_backup)
            # if os.path.exists(self.service_base):
            #     service_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.service_base)))
            #     service_backup = os.path.join(backups, service_ctime + self.service_base)
            #     shutil.move(self.service_base, service_backup)
            if os.path.exists(self.model_base):
                model_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.model_base)))
                model_backup = os.path.join(backups, model_ctime + self.model_base)
                shutil.move(self.model_base, model_backup)
        else:  # 如果不保留老版本则删除
            if os.path.exists(self.controller_base):
                shutil.rmtree(self.controller_base)
            # if os.path.exists(self.service_base):
            #     shutil.rmtree(self.service_base)
            if os.path.exists(self.model_base):
                shutil.rmtree(self.model_base)

        # 如果base_dir不存在则新建
        if not os.path.exists(self.controller_base):
            os.mkdir(self.controller_base)
            with open(os.path.join(self.controller_base, '__init__.py'), 'w') as controller_init: pass
        # if not os.path.exists(self.service_base):
        #     os.mkdir(self.service_base)
        #     with open(os.path.join(self.service_base, '__init__.py'), 'w') as  service_init: pass
        if not os.path.exists(self.model_base):
            os.mkdir(self.model_base)
            with open(os.path.join(self.model_base, '__init__.py'), 'w') as model_init: pass
        if not os.path.exists('__init__.py'):
            with open('__init__.py', 'w') as init: pass

    def get_model_meta(self, model_key: str):
        s1 = model_key.replace('«', '_').replace('»', '').replace(',', '')
        s2 = camel_case_to_under_score(s1)
        model_file = s2.replace('__', '_').replace('data_result_paged_list', 'drpl').replace('data_result_list', 'drl').replace(
            'data_result', 'dr').replace('paged_list', 'pl').replace('page_data_response', 'pdr').replace('page_response', 'pr')
        model_class = ''.join([s.title() for s in model_file.split('_')])
        return Model(model_file, model_class)

    def get_path_name(self, path):
        path = path.replace('-', '_')  # resolve /by-key/{key}
        parts = path.split('/')
        if re.match('^v[1-9]+$', parts[1]):
            return ('_'.join(parts[2:]).replace('{', '').replace('}', '') + '_' + parts[1]).lower()
        else:
            return ('_'.join(parts[1:]).replace('{', '').replace('}', '')).lower()

    def get_path_meta(self, path: str):
        path = path.replace('.', '')  # /pause.json
        path_name = self.get_path_name(path)
        path_name_pieces = []
        for piece in path_name.split('_'):
            if piece not in path_name_pieces or (piece in path_name_pieces and piece != path_name_pieces[-1]):
                path_name_pieces.append(piece)

        path_file = '_'.join(path_name_pieces)
        path_class = ''.join([s.title() for s in path_file.split('_')])
        return Path(path_file, path_class)

    def run(self):
        if os.path.isfile(self.swagger_doc):
            j = json.load(open(self.swagger_doc))
        elif re.match('^http.*', self.swagger_doc):
            j = requests.get(self.swagger_doc).json()
        else:
            raise Exception('No swagger-doc [json file or api-doc url] provided.')

        self.swagger_version = j.get('swagger')
        self.service_info: dict = j.get('info')
        self.service_host = j.get('host')
        self.base_path = j.get('basePath')
        self.api_paths: dict = j.get('paths')
        self.model_definitions: dict = j.get('definitions')

        # ① generate models
        for model_key in self.model_definitions.keys():
            model_meta = self.get_model_meta(model_key)
            print('Model Key:', model_key)
            print('Model File:', model_meta.model_file)
            print('Model Class:', model_meta.model_class)
            print()

            model: dict = self.model_definitions.get(model_key)

            import_rows = {'from easy.base.model_base import ModelBase'}
            class_row = "class %s(ModelBase):\n" % model_meta.model_class
            init_row = "%sdef __init__(self, %%s):\n" % sp4
            fields = []
            lines = []
            field_descriptions = []

            properties: dict = model.get('properties')
            if properties:
                for field_name in properties.keys():
                    field: dict = properties.get(field_name)
                    field_type = field.get('type')
                    field_format = field.get('format')
                    field_ref: str = field.get('$ref')
                    field_description = field.get('description')

                    field_descriptions.append(
                        '%s:param %s: %s' % (sp8, field_name, field_description)) if field_description else None

                    if field_ref:  # 引用对象
                        ref_model_meta = self.get_model_meta(field_ref.lstrip('#/definitions/'))
                        if ref_model_meta.model_file != model_meta.model_file and ref_model_meta.model_class != model_meta.model_class:
                            import_rows.add('from .%s import %s' % (ref_model_meta.model_file, ref_model_meta.model_class))
                            fields.append('%s: %s = None' % (field_name, ref_model_meta.model_class))
                        else:  # 兼容类型递归引用自己
                            fields.append('%s: "%s" = None' % (field_name, ref_model_meta.model_class))
                        lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                    elif field_type == 'array':  # 引用数组
                        import_rows.add('from typing import List')
                        item_ref: str = field['items'].get('$ref')
                        item_type: str = field['items'].get('type')
                        item_format: str = field['items'].get('format')
                        if item_ref:  # 数组类型为对象
                            item_model_meta = self.get_model_meta(item_ref.lstrip('#/definitions/'))
                            if item_model_meta.model_file != model_meta.model_file and \
                                    item_model_meta.model_class != model_meta.model_class:
                                import_rows.add('from .%s import %s' % (item_model_meta.model_file, item_model_meta.model_class))
                                fields.append('%s: List[%s] = None' % (field_name, item_model_meta.model_class))
                            else:  # 兼容类型递归引用自己
                                fields.append('%s: List["%s"] = None' % (field_name, item_model_meta.model_class))
                            lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                        else:  # 数组元素为其它
                            _item_type = swagger_type_to_python(swagger_type=item_type, format=item_format)
                            fields.append('%s: List[%s] = None' % (field_name, _item_type))
                            lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                    else:  # 其它
                        _field_type = swagger_type_to_python(field_type, field_format)
                        fields.append('%s: %s = None' % (field_name, _field_type))
                        lines.append('%sself.%s = %s' % (sp8, field_name, field_name))

                description_content = '%s"""\n%s\n%s"""\n' % (
                    sp8, '\n'.join(field_descriptions), sp8) if field_descriptions else None

                init_row = init_row % ', '.join(fields)
                wrapped_init_row = wrap_line(init_row)

                import_rows = list(import_rows)
                import_rows.sort()  # set 无序导致import 出现 gitdiff

                model_file = os.path.join(self.model_base, model_meta.model_file + '.py')
                with open(model_file, 'w', encoding='utf8') as f_model:
                    f_model.writelines('"""code generated by a tool, do not modify."""\n\n')
                    f_model.writelines('\n'.join(import_rows))
                    f_model.writelines('\n' * 3)
                    f_model.writelines(class_row)
                    f_model.writelines(wrapped_init_row)
                    f_model.writelines(description_content) if description_content else None
                    f_model.writelines('\n'.join(lines))
                    f_model.writelines('\n')

            else:
                print('***IGNORE***', model_key, '***IGNORE***\n')

        # TODO ② generate controllers
        for path in self.api_paths:
            if self.excluded_paths and path in self.excluded_paths:
                continue  # 跳过path排除列表
            if self.included_paths and path not in self.included_paths:
                continue  # 如果有指定处理的path列表，则跳过其它
            self.current_path = path  # just for debug global evaluate
            print('PATH Key:', path)

            request_path = path

            for api_base in self.api_bases:  # 缩短 controllers 文件和类名
                self.current_path = self.current_path.replace(api_base, '')

            path_meta = self.get_path_meta(self.current_path)
            print('PATH File:', path_meta.path_file)
            print('PATH Class:', path_meta.path_class)
            print()

            controller_file = os.path.join('controller', path_meta.path_file + '_controller.py')
            controller_class = path_meta.path_class + 'Controller'

            controller_imports = {'from easy.base.service_base import ServiceBase', 'from easy.base.service_hooks import chk_http'}
            controller_class_row = 'class %s(ServiceBase):\n' % controller_class

            controller_init = "%sdef __init__(self, host, **kwargs):\n" % sp4
            controller_path_doc = sp8 + '"""%s"""\n' % path
            controller_super = sp8 + 'super(%s, self).__init__(host=host, **kwargs)' % controller_class

            controller_init_spec = wrap_line(controller_init) + controller_path_doc + wrap_line(controller_super)

            controller_methods = []
            summary_list = []
            methods = self.api_paths.get(path)
            for method in methods.keys():
                method_content = methods.get(method)
                summary = (method_content.get('summary', '') + sp + method_content.get('description', '')).strip()
                operationId = method_content.get('operationId')
                parameters: List[dict] = method_content.get('parameters')
                responses = method_content.get('responses')
                response200: dict = responses.get('200')  # presume always exist.
                if response200 and 'schema' in response200:
                    response200_schema = response200.get('schema')
                else:
                    continue  # response200时没有 schema 存在
                method_field_descriptions = []

                if '$ref' in response200_schema:
                    resp_ref_meta = self.get_model_meta(response200_schema['$ref'].lstrip('#/definitions/'))
                    controller_imports.add('from ..model.%s import %s' % (resp_ref_meta.model_file, resp_ref_meta.model_class))
                else:
                    resp_ref_meta = None

                summary_list.append("{0:<8}{1}\t{2}".format(method.upper(), path, summary or ''))

                path_params = []
                path_param_names = []
                query_params = []
                load_param_name = load_param = None
                json_param_name = json_param = None
                header_params = []

                if parameters:
                    for parameter in parameters:
                        param_name = parameter.get('name')
                        param_description = parameter.get('description')
                        param_type = parameter.get('type')
                        param_format = parameter.get('format')
                        if param_name != param_description:
                            method_field_descriptions.append('%s:param %s: %s' % (sp8, param_name, param_description))
                        if parameter.get('in') == 'body':
                            param_schema = parameter.get('schema')
                            if '$ref' in param_schema:
                                ref_meta = self.get_model_meta(param_schema['$ref'].lstrip('#/definitions/'))
                                ref_file = ref_meta.model_file
                                ref_class = ref_meta.model_class
                                controller_imports.add('from ..model.%s import %s' % (ref_file, ref_class))
                                load_param_name = param_name
                                load_param = "%s: %s = None" % (param_name, ref_class)
                            elif 'type' in param_schema and param_schema['type'] == 'array':
                                controller_imports.add('from typing import List')
                                items: dict = param_schema.get('items')
                                if items:
                                    item_type = items.get('type')
                                    item_format = items.get('format')
                                    json_param_name = param_name
                                    json_param = '%s: List[%s] = None' % (
                                        param_name, swagger_type_to_python(item_type, item_format))
                        elif parameter.get('in') == 'path':
                            request_path = re.sub('{%s}' % param_name, '%s', request_path)
                            path_param_names.append(param_name)
                            path_params.append('%s: %s = None' % (param_name, swagger_type_to_python(param_type, param_format)))
                        elif parameter.get('in') == 'query':
                            query_params.append("'%s': None" % param_name)
                        elif parameter.get('in') == 'formData':
                            pass
                        elif parameter.get('in') == 'header':
                            header_params.append("'%s': None" % param_name)
                        else:
                            raise Exception('parameter "in" type[%s] unknown' % parameter)

                controller_method = "%sdef _%s(self" % (sp4, operationId)
                shadow_method = "\n\n%sdef %s(self" % (sp4, operationId)
                shadow_return = "\n%sreturn getattr(self._%s(" % (sp8, operationId)

                if path_params:
                    controller_method += ', ' + ', '.join(path_params)
                    shadow_method += ', ' + ', '.join(path_params)
                    shadow_return += ', '.join(['{0}={0}'.format(path_param.split(':')[0]) for path_param in path_params]) + ', '
                if load_param:
                    controller_method += ', %s' % load_param
                    shadow_method += ', %s' % load_param
                    shadow_return += '{0}={0}'.format(load_param.split(':')[0]) + ', '
                if json_param:
                    controller_method += ', %s' % json_param
                    shadow_method += ', %s' % json_param
                    shadow_return += '{0}={0}'.format(json_param.split(':')[0]) + ', '
                if query_params:
                    controller_method += ', ' + 'params={%s}' % ', '.join(query_params)
                    shadow_method += ', ' + 'params={%s}' % ', '.join(query_params)
                    shadow_return += 'params=params, '
                if header_params:
                    controller_method += ', ' + 'headers={%s}' % ','.join(header_params)
                    shadow_method += ', ' + 'headers={%s}' % ','.join(header_params)
                    shadow_return += 'headers=headers, '

                controller_method += ', **kwargs):'  # controller声明结束
                shadow_method += ', should=True, http=200, **kwargs):'
                shadow_return += "hook_funcs=[[chk_http, should, http]], **kwargs), 'model', None)"

                doc_str = '\n'
                if summary:
                    doc_str += sp8 + '"""\n' + sp8 + summary
                if method_field_descriptions:
                    doc_str += '\n'
                    doc_str += '\n'.join(method_field_descriptions)
                if resp_ref_meta:
                    doc_str += '\n%s:rtype: %s' % (sp8, resp_ref_meta.model_class)
                if doc_str:
                    doc_str += '\n%s"""' % sp8

                request_line = '\n' + sp8 + "return self.%s('%s'" % (method, request_path)
                if path_param_names:
                    request_line += " %% (%s)" % (', '.join(path_param_names)) + ','
                else:
                    request_line += ','

                if load_param_name:
                    request_line += sp + 'load=' + load_param_name + ','
                if json_param_name:
                    request_line += sp + 'json=' + json_param_name + ','
                if query_params:
                    request_line += ' params=params,'
                if header_params:
                    request_line += ' headers=headers,'
                if resp_ref_meta:  # controller中使用默认（swagger）model 处理，可以在调用处（service 中）使用'M=Model.to_model'覆盖
                    request_line += ' model_hook=%s.to_model,' % resp_ref_meta.model_class
                request_line += ' **kwargs)'

                request_line = wrap_line(request_line)
                controller_method += request_line
                controller_method += shadow_method + doc_str + shadow_return
                controller_methods.append(controller_method)

            controller_imports = list(controller_imports)
            controller_imports.sort()  # set 无序导致import 出现 gitdiff

            content = '"""\ncode generated by a tool, do not modify.%s\n"""\n\n' % (
                '\n' * 2 + '\n'.join(summary_list) if summary_list else '')
            content += '\n'.join(controller_imports)
            content += '\n' * 3
            content += controller_class_row
            content += controller_init_spec
            content += '\n' * 2
            content += '\n\n'.join(controller_methods)
            content += '\n'

            content = autopep8.fix_code(content, options={'aggressive': 2, 'in_place': True, 'max_line_length': 140}, encoding='utf-8')

            with open(controller_file, 'w') as f_controller:
                f_controller.writelines(content)


def __get_run_args():
    arg_parser = argparse.ArgumentParser('')
    arg_parser.add_argument('-A', '--swagger-doc', action='store', dest='swagger_doc',
                            help='swagger json文档url地址,如: http://app.com/v2/api-docs')
    arg_parser.add_argument('--api-bases', action='store', nargs='+', default=[], dest='api_bases',
                            help='在controller文件和类名中忽略该字符串，如：--api-bases=/a/b /path')
    arg_parser.add_argument('-B', '--code-base', action='store', dest='code_base', required=False, help='生成代码目标目录绝对路径[必填]')
    arg_parser.add_argument('-M', '--model-base', action='store', dest='model_base', default='model', help='model目标目录')
    arg_parser.add_argument('-C', '--controller-base', action='store', dest='controller_base', default='controller',
                            help='controller目标目录')
    arg_parser.add_argument('-S', '--service-base', action='store', dest='service_base', default='service', help='service目标目录')
    arg_parser.add_argument('-P', '--included-paths', action='store', nargs='+', dest='included_paths', help='待处理的接口列表,不填写则处理全部')
    arg_parser.add_argument('-E', '--excluded-paths', action='store', nargs='+', dest='excluded_paths', help='排除的待处理接口列表')
    arg_parser.add_argument('-K', '--keep', action='store', type=bool, dest='keep', default=True, help='是否保留老版本，默认为True')
    arg_parser.add_argument('-T', '--target-relative-dir', action='store', dest='target_relative_dir', help='保存代码时相对于当前目录的相对路径')

    arg_parser.add_argument('-O', '--out-box', action='store', dest='out_box', default=False, type=bool, help='')
    arg_parser.add_argument('-W', '--app-where', action='store', dest='app_where')
    arg_parser.add_argument('-N', '--app-name', action='store', dest='app_name', type=str, help='如：classec-search-api')
    arg_parser.add_argument('-V', '--app-version', action='store', dest='app_version', type=str, help='如：master、develop、')
    arg_parser.add_argument('-p', '--pip-name', action='store', dest='pip_name', help='需要制定pip版本如pip3.6、pip3.8')

    args = arg_parser.parse_args()

    if not args.out_box:
        assert args.code_base, '生成代码目标目录绝对路径[必填]'
        assert os.getcwd() == args.code_base, '为防止误操作导致覆盖，需提前 cd 的操作目录，--code-base 参数必须提供且与当前目录一致[绝对路径]。\ncurrent-dir：%s, ' \
                                              '\n--code-base：%s' % (os.getcwd(), args.code_base)

        # assert os.path.split(args.code_base)[-2].endswith('autotest')
        config_file = os.path.join(args.code_base, 'pycodegenconfig.json')
        if os.path.exists(config_file):
            with open(config_file) as f:
                config: dict = json.load(f)
                args.swagger_doc = config['swagger_doc'] if not args.swagger_doc and 'swagger_doc' in config else args.swagger_doc
                args.api_bases = config['api_bases'] if not args.api_bases and 'api_bases' in config else args.api_bases
                args.model_base = config['model_base'] if not args.model_base and 'model_base' in config else args.model_base
                args.controller_base = config['controller_base'] if not args.controller_base and config.get(
                    'controller_base') else args.controller_base
                args.service_base = config['service_base'] if not args.service_base and config.get(
                    'service_base') else args.service_base
                args.included_paths = config['included_paths'] if not args.included_paths and config.get(
                    'included_paths') else args.included_paths
                args.excluded_paths = config['excluded_paths'] if not args.excluded_paths and config.get(
                    'excluded_paths') else args.excluded_paths
                args.target_relative_dir = config.get('target_relative_dir') or args.target_relative_dir
    else:
        assert args.app_where and os.path.exists(os.path.expanduser(args.app_where)), 'whl目标路径不存在'
        assert args.app_name, '--out-box时--app-name参数必需设置'
        assert args.app_version, '--out-box时--app-version参数必需设置'

    return args


def main():
    args = __get_run_args()
    pycodegen = PyCodeGen(args=args)
    pycodegen.run() if not args.out_box else None


if __name__ == '__main__':
    start = datetime.now()
    main()
    end = datetime.now()
    print('用时：', (end - start).total_seconds(), '秒')
