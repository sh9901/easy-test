import sys
import os
import shutil
import argparse
import json
import time
import requests
from collections import namedtuple

sp = " "
sp4 = sp * 4
sp8 = sp * 8
sp12 = sp * 12
sp16 = sp * 16

Model = namedtuple('model', ['model_file', 'model_class'])


def swagger_type_to_python_type(swagger_type, format=None):
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
        return swagger_type


def camel_case_to_under_score(camel_case):
    return ''.join(map(lambda x: x if (x.islower() or x == '_' or str(x).isdigit()) else '_' + x.lower(), camel_case)).lstrip('_')


def wrap_init_line(line, max_len):
    if len(line) < max_len:
        return line
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
                current_line += sp16 + section + ','
                is_first_row = False
        else:
            current_line = sp16 + current_line if not current_line.startswith(sp16) else current_line
            try_len = len(current_line + section)
            if try_len < max_len:
                current_line += section + ','
            else:
                wrapped_line += current_line + '\n'
                current_line = ''
                current_line = sp16 + current_line if not current_line.startswith(sp16) else current_line
                current_line += section + ','

    if current_line:
        wrapped_line += current_line

    return wrapped_line.rstrip(',')


class PyCodeGen(object):

    def __init__(self, args):
        self.swagger_doc = args.swagger_doc
        self.code_base = args.code_base
        self.controller_base = args.controller_base
        self.service_base = args.service_base
        self.model_base = args.model_base
        self.included_paths = args.included_paths
        self.excluded_paths = args.excluded_paths

        if self.swagger_doc and self.code_base:
            # 如果代码目录、swagger doc地址已获取，则初始化项目目录结构
            self.init_base_dir(args.keep)
        else:
            print('swagger_doc没有提供且没有自动获取到，退出处理')
            sys.exit(-1)

    def init_base_dir(self, keep):
        if keep:  # 如果保留老版本则先备份
            backups = "backups"
            backupstamp = '%Y%m%d%H%M%S_'
            if not os.path.exists(backups):
                os.mkdir(backups)
            if os.path.exists(self.controller_base):
                controoler_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.controller_base)))
                controller_backup = os.path.join(backups, controoler_ctime + self.controller_base)
                shutil.move(self.controller_base, controller_backup)
            if os.path.exists(self.service_base):
                service_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.service_base)))
                service_backup = os.path.join(backups, service_ctime + self.service_base)
                shutil.move(self.service_base, service_backup)
            if os.path.exists(self.model_base):
                model_ctime = time.strftime(backupstamp, time.localtime(os.path.getctime(self.model_base)))
                model_backup = os.path.join(backups, model_ctime + self.model_base)
                shutil.move(self.model_base, model_backup)
        else:  # 如果不保留老版本则删除
            if os.path.exists(self.controller_base):
                shutil.rmtree(self.controller_base)
            if os.path.exists(self.service_base):
                shutil.rmtree(self.service_base)
            if os.path.exists(self.model_base):
                shutil.rmtree(self.model_base)

        # 如果base_dir不存在则新建
        if not os.path.exists(self.controller_base):
            os.mkdir(self.controller_base)
            with open(os.path.join(self.controller_base, '__init__.py'), 'w') as controller_init: pass
        if not os.path.exists(self.service_base):
            os.mkdir(self.service_base)
            with open(os.path.join(self.service_base, '__init__.py'), 'w') as  service_init: pass
        if not os.path.exists(self.model_base):
            os.mkdir(self.model_base)
            with open(os.path.join(self.model_base, '__init__.py'), 'w') as model_init: pass
        if not os.path.exists('__init__.py'):
            with open('__init__.py', 'w') as init: pass

    def get_model_meta(self, model_key: str):
        s1 = model_key.replace('«', '_').replace('»', '').replace(',', '')
        s2 = camel_case_to_under_score(s1)
        model_file = s2.replace('__', '_').replace('data_result_paged_list', 'drpl').replace('data_result_list', 'drl').replace(
            'data_result', 'dr').replace('paged_list', 'pl')
        model_class = ''.join([s.title() for s in model_file.split('_')])
        return Model(model_file, model_class)

    def run(self):
        j = requests.get(self.swagger_doc).json()

        self.swagger_version = j.get('swagger')
        self.service_info: dict = j.get('info')
        self.service_host = j.get('host')
        self.base_path = j.get('basePath')
        self.service_paths: dict = j.get('paths')
        self.service_definitions: dict = j.get('definitions')

        # ① generate models
        for model_key in self.service_definitions.keys():
            model_meta = self.get_model_meta(model_key)
            print(model_key)
            print(model_meta.model_file)
            print(model_meta.model_class)
            print()

            model: dict = self.service_definitions.get(model_key)

            import_rows = {'from easy.base.model_base import ModelBase'}
            class_row = "class %s(ModelBase):\n" % model_meta.model_class
            init_row = "%sdef __init__(self, %%s):\n" % sp4
            fields = []
            lines = []
            field_descriptions = []

            print(model_key)
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
                        import_rows.add('from .%s import %s' % (ref_model_meta.model_file, ref_model_meta.model_class))
                        fields.append('%s: %s = None' % (field_name, ref_model_meta.model_class))
                        lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                    elif field_type == 'array':  # 引用数组
                        import_rows.add('from typing import List')
                        item_ref: str = field['items'].get('$ref')
                        item_type: str = field['items'].get('type')
                        item_format: str = field['items'].get('format')
                        if item_ref:  # 数组类型为对象
                            item_model_meta = self.get_model_meta(item_ref.lstrip('#/definitions/'))
                            import_rows.add('from .%s import %s' % (item_model_meta.model_file, item_model_meta.model_class))
                            fields.append('%s: List[%s] = None' % (field_name, item_model_meta.model_class))
                            lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                        else:  # 数组元素为其它
                            _item_type = swagger_type_to_python_type(swagger_type=item_type, format=item_format)
                            fields.append('%s: List[%s] = None' % (field_name, _item_type))
                            lines.append('%sself.%s = %s' % (sp8, field_name, field_name))
                    else:  # 其它
                        _field_type = swagger_type_to_python_type(field_type, field_format)
                        fields.append('%s: %s = None' % (field_name, _field_type))
                        lines.append('%sself.%s = %s' % (sp8, field_name, field_name))

                description_content = '%s"""\n%s\n%s"""\n' % (
                    sp8, '\n'.join(field_descriptions), sp8) if field_descriptions else None

                init_row = init_row % ', '.join(fields)
                wrapped_init_row = wrap_init_line(init_row, 130)

                model_file = os.path.join(self.model_base, model_meta.model_file + '.py')
                with open(model_file, 'w', encoding='utf8') as f_model:
                    f_model.writelines('\n'.join(import_rows))
                    f_model.writelines('\n' * 3)
                    f_model.writelines(class_row)
                    f_model.writelines(wrapped_init_row)
                    f_model.writelines(description_content) if description_content else None
                    f_model.writelines('\n'.join(lines))

            else:
                print('***IGNORE***', model_key, '***IGNORE***\n')

        # TODO ② generate controllers


def __get_run_args():
    arg_parser = argparse.ArgumentParser('')
    arg_parser.add_argument('-A', '--swagger-doc', action='store', dest='swagger_doc',
                            help='swagger json文档url地址,如: http://app.com/v2/api-docs')
    arg_parser.add_argument('-B', '--code-base', action='store', dest='code_base', required=True, help='生成代码目标目录')
    arg_parser.add_argument('-M', '--model-base', action='store', dest='model_base', default='model', help='model目标目录')
    arg_parser.add_argument('-C', '--controller-base', action='store', dest='controller_base', default='controller',
                            help='controller目标目录')
    arg_parser.add_argument('-S', '--service-base', action='store', dest='service_base', default='service', help='service目标目录')
    arg_parser.add_argument('-P', '--included-paths', action='store', nargs='+', dest='included_paths', help='待处理的接口列表,不填写则处理全部')
    arg_parser.add_argument('-E', '--excluded-paths', action='store', nargs='+', dest='excluded_paths', help='排除的待处理接口列表')
    arg_parser.add_argument('-K', '--keep', action='store', type=bool, dest='keep', default=True, help='是否保留老版本，默认为True')

    args = arg_parser.parse_args()

    assert os.getcwd() == args.code_base, '为防止误操作导致覆盖，需提前 cd 的操作目录，--code-base 参数必须提供且与当前目录一致。\ncurrent-dir：%s, ' \
                                          '\n--code-base：%s' % (os.getcwd(), args.code_base)
    assert os.path.split(args.code_base)[-2].endswith('autotest')

    config_file = os.path.join(args.code_base, 'pycodegenconfig.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            config: dict = json.load(f)
            args.swagger_doc = config['swagger_doc'] if not args.swagger_doc and 'swagger_doc' in config else args.swagger_doc
            args.model_base = config['model_base'] if not args.model_base and 'model_base' in config else args.model_base
            args.controller_base = config['controller_base'] if not args.controller_base and config.get(
                'controller_base') else args.controller_base
            args.service_base = config['service_base'] if not args.service_base and config.get(
                'service_base') else args.service_base
            args.included_paths = config['included_paths'] if not args.included_paths and config.get(
                'included_paths') else args.included_paths
            args.excluded_paths = config['excluded_paths'] if not args.excluded_paths and config.get(
                'excluded_paths') else args.excluded_paths

    return args


def main():
    args = __get_run_args()
    pycodegen = PyCodeGen(args=args)
    pycodegen.run()


if __name__ == '__main__':
    main()
