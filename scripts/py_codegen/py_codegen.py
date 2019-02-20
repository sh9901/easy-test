import sys
import os
import shutil
import argparse
import json
import re
import requests
from datetime import datetime

sp = " "
sp4 = sp * 4
sp8 = sp * 8
sp12 = sp * 12
stamp_fmt = "__%Y%m%d_%H%M%S__"
stamp_pattern = ".+__[\d]{8}_[\d]{6}__.py$"
typing_list_patter = re.compile('List\[.+\]')


def get_controller_name_from_path0(path):
    parts = path.split('/')
    if re.match('^v[1-9]+$', parts[1]):
        return parts[1].lower(), parts[2]
    else:
        return '', parts[1]


def get_controller_name_from_path(path):
    parts = path.split('/')
    if re.match('^v[1-9]+$', parts[1]):
        return parts[1].lower(), ''.join(parts[2:]).replace('{', '').replace('}', '')
    else:
        return '', ''.join(parts[1:]).replace('{', '').replace('}', '')


def get_controller_file_prefix(controller_name):
    return ''.join(map(lambda x: x if (x.islower() or x == '_') else '_' + x.lower(), controller_name))


def get_controller_object_prefix(controller_name):
    return controller_name.title().replace('_', '')


def try_get_swagger_doc_from_readme(readme_path):
    if not os.path.exists(readme_path):
        print('')
        sys.exit(-1)
    else:
        pattern = re.compile("(\[api_?doc.+\]|\[swagger_?doc.+\]){1}\((http://.*)\)$", re.IGNORECASE)
        with open(readme_path) as f:
            lines = f.readlines()
            for line in lines:
                matches = pattern.match(line)
                if matches:
                    return matches.groups()[-1]
        print('')
        sys.exit(-1)


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


class PyCodeGen(object):

    def __init__(self, args):
        # 如果生成的文件已存在，则新建版本
        self.stamp = datetime.now().strftime(stamp_fmt)
        self.swagger_doc = args.swagger_doc
        self.project_path_base = args.project_path_base
        self.code_base = args.code_base
        self.included_paths = args.included_paths
        self.excluded_paths = args.excluded_paths

        self.controller_base = args.controller_base
        self.service_base = args.service_base
        self.model_base = args.model_base

        self.controller_real_files = {}
        self.service_real_files = {}
        self.ref_real_file = {}

        if not self.code_base:
            # 如果没有指定代码目标目录，则取当前目录
            self.code_base = os.getcwd()
            readme_path = os.path.join(self.code_base, 'readme.md')
            if not self.swagger_doc and os.path.exists(readme_path):
                # 如果没有指定swagger_doc，则尝试从当前目录下readme中尝试查找
                self.swagger_doc = try_get_swagger_doc_from_readme(readme_path)

        if self.swagger_doc and self.code_base:
            # 如果代码目录、swagger doc地址已获取，则初始化项目目录结构
            self.init_base_dir(args.keep)
        else:
            print('swagger_doc没有提供且没有自动获取到，退出处理')
            sys.exit(-1)

    def init_base_dir(self, keep):
        if not keep:  # 如果不保留老版本则先删除
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

    def run(self):
        j = requests.get(self.swagger_doc).json()

        self.swagger_version = j.get('swagger')
        self.service_info: dict = j.get('info')
        self.service_host = j.get('host')
        self.base_path = j.get('basePath')
        self.service_paths: dict = j.get('paths')
        self.service_definitions: dict = j.get('definitions')

        paths = self.service_paths.keys()
        for path in paths:
            if self.excluded_paths and path in self.excluded_paths:
                continue  # 跳过path排除列表
            if self.included_paths and path not in self.included_paths:  # 如果有指定处理的path列表，则跳过其它
                continue
            self.current_path = path  # just for debug global evaluate
            print('PATH:', path)
            controller_version, controller_name = get_controller_name_from_path(path)

            controller_file_prefix = get_controller_file_prefix(controller_name)
            controller_object_prefix = get_controller_object_prefix(controller_name)

            controller_class = controller_object_prefix + 'Controller'
            controller_file_base = controller_file_prefix + '_controller.py'
            controller_file = os.path.join(self.controller_base, controller_file_base)
            if not controller_file in self.controller_real_files:
                if not os.path.exists(controller_file):
                    self.controller_real_files[controller_file] = controller_file
                else:
                    controller_file_base = controller_file_prefix + '_controller%s.py' % self.stamp
                    self.controller_real_files[controller_file] = os.path.join(self.controller_base, controller_file_base)

            service_class = controller_object_prefix + 'Service'
            service_file_base = controller_file_prefix + '_service.py'
            service_file = os.path.join(self.service_base, service_file_base)
            if not service_file in self.service_real_files:
                if not os.path.exists(service_file):
                    self.service_real_files[service_file] = service_file
                else:
                    service_file_base = controller_file_prefix + '_service%s.py' % self.stamp
                    self.service_real_files[service_file] = os.path.join(self.service_base, service_file_base)

            path_content = self.service_paths[path]
            http_methods = path_content.keys()

            controller_imports = {'from easy.base.service_base import ServiceBase'}
            controller_class_row = 'class %s(ServiceBase):' % controller_class
            controller_init_row = "    def __init__(self, host):\n        super(%s, self).__init__(host)" % (controller_class)
            controller_methods = []

            service_imports = {"from %s.%s.%s import %s" % (self.project_path_base, self.controller_base, os.path.splitext(os.path.basename(controller_file))[0], controller_class)}

            service_class_row = "class %s(object):" % service_class
            service_init_row = "%sdef __init__(self, host):\n%sself.controller = %s(host=host)" % (sp4, sp8, controller_class)
            service_methods = []

            for http_method in http_methods:
                http_method = http_method.lower()
                method = path_content[http_method]
                # tag_text = ','.join(method['tags'])
                summary_text = method.get('summary', '')
                comment = ','.join(method['tags']) + '-' + summary_text
                operationId = self.get_operator_id(method['operationId'], controller_version)  # swagger operationId转换如：/v1/getMenteeUsingPOST -> get_mentee_v1

                parameters: list = self.build_parameters(method)
                response200: dict = self.build_response200(method)
                service_imports.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(response200['ref_file']))[0], response200['ref_class']))

                # 1. write parameters model
                self.write_parameters(parameters)

                # 2. write response model
                self.write_response200(response200)

                controller_method = "%sdef %s(self" % (sp4, operationId)
                service_method = "%sdef m_%s(self, undefined_params=None, should=True, info=None, **kwargs) -> %s:\n" % (sp4, operationId, response200['ref_class'])
                service_method += "%s# TODO - NotImplemented Yet.\n" % (sp8)
                service_method += "%sresp = self.controller.%s(undefined_params, M=%s.to_model, info=info, **kwargs)\n" % (sp8, operationId, response200['ref_class'])
                service_method += "%sif resp.status_code == 200:\n" % (sp8)
                service_method += "%smodel: %s = resp.model\n" % (sp12, response200['ref_class'])
                service_method += "%sreturn model\n" % (sp12)
                service_method += "%selse:\n" % (sp8)
                service_method += "%sself.controller.raise_exception(request=undefined_params, response=resp, should_success=should, message='%s-失败')\n" % (sp12, comment)

                service_methods.append(service_method)

                path_params = []
                query_params = {}
                load_param = None
                for parameter in parameters:
                    controller_method += ', %s: %s = None' % (parameter['name'], parameter['type'])
                    if parameter['in'] == 'path':
                        path = re.sub('{%s}' % parameter['name'], '%s', path)
                        path_params.append(parameter['name'])
                    if parameter['in'] == 'query':
                        query_params[parameter['name']] = parameter['name']

                    if 'ref_class' in parameter:
                        load_param = parameter['name']  # 只有一个
                        ref_class = parameter['ref_class']
                        ref_file = parameter['ref_file']
                        controller_imports.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(ref_file))[0], ref_class))
                        service_imports.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(ref_file))[0], ref_class))

                    # 是否有typing.List
                    if typing_list_patter.match(parameter.get('type', '')):
                        controller_imports.add("from typing import List")
                        service_imports.add("from typing import List")

                controller_method += ', **kwargs):\n'  # controller声明结束

                # 描述
                if comment:
                    controller_method += '%s"""%s"""\n' % (sp8, comment)

                # query 声明处理
                if query_params:
                    query_params_str = json.dumps(query_params)
                    controller_method += query_params_str
                else:
                    query_params_str = None

                # path 处理
                controller_method += "%sreturn self.%s('%s'" % (sp8, http_method, path)
                if path_params:
                    controller_method += " %% (%s)" % (','.join(path_params))

                # load处理
                if load_param:
                    controller_method += ", load=%s" % (load_param)

                # query 插入处理
                if query_params_str:
                    controller_method += ", params=query_params"

                controller_method += ", **kwargs)"  # controller 方法定义结束

                controller_methods.append(controller_method)

            # 3. write controller
            with open(controller_file, 'w', encoding='utf8') as f_controller:
                f_controller.writelines('\n'.join(controller_imports))
                f_controller.writelines('\n' * 3)
                f_controller.writelines(controller_class_row)
                f_controller.writelines('\n')
                f_controller.writelines(controller_init_row)
                f_controller.writelines('\n' * 2)
                f_controller.writelines('\n\n'.join(controller_methods))

            # 4. write service
            with open(service_file, 'w', encoding='utf8') as f_service:
                f_service.writelines('\n'.join(service_imports))
                f_service.writelines('\n' * 3)
                f_service.writelines(service_class_row)
                f_service.writelines('\n')
                f_service.writelines(service_init_row)
                f_service.writelines('\n' * 2)
                f_service.writelines('\n\n'.join(service_methods))

    def write_parameters(self, parameters: list):
        for parameter in parameters:
            if parameter.get('in') == 'body':
                if parameter.get('ref_class'):
                    model_import = {"from easy.base.model_base import ModelBase"}
                    ref_class = parameter['ref_class']
                    ref_file = parameter['ref_file']
                    ref_fields = parameter['ref_fields']
                    self.write_nested_ref(ref_fields)  # 递归写嵌套ref_fields, 如果ref_fields里有model类型字段的话
                    model_typed_field_list = []
                    # model_raw_field_list = []
                    lines = ""
                    for field in ref_fields:
                        if 'ref_class' in field:
                            iref_class = field['ref_class']
                            iref_file = field['ref_file']
                            model_import.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(iref_file))[0], iref_class))
                        if typing_list_patter.match(field.get('type', '')):
                            model_import.add("from typing import List")

                        if 'type' in field:
                            model_typed_field_list.append('%s: %s = None' % (field['name'], field['type']))
                        else:
                            model_typed_field_list.append('%s = None' % field['name'])

                        # model_raw_field_list.append(field['name'])
                        f_description = '#' + field['description'] if field.get('description') else ''
                        lines += "%sself.%s = %s%s%s\n" % (sp8, field['name'], field['name'], sp4, f_description)

                    import_rows = '\n'.join(model_import)
                    class_row = "class %s(ModelBase):" % (ref_class)
                    init_row = "    def __init__(self, %s):" % (', '.join(model_typed_field_list))
                    # lines = "".join(["        self.%s = %s\n" % (x, x) for x in model_raw_field_list])
                    with open(ref_file, 'w', encoding='utf8') as f:
                        f.writelines(import_rows)
                        f.writelines('\n' * 3)
                        f.writelines(class_row)
                        f.writelines('\n')
                        f.writelines(init_row)
                        f.writelines('\n')
                        f.writelines(lines)

    def write_response200(self, response: dict):
        if 'ref' in response:
            model_import = {"from easy.base.model_base import ModelBase"}
            ref_class = response['ref_class']
            ref_file = response['ref_file']
            ref_fields = response['ref_fields']
            self.write_nested_ref(ref_fields)
            model_typed_field_list = []
            # model_raw_field_list = []
            lines = ""
            for field in ref_fields:
                if 'ref_class' in field:
                    iref_class = field['ref_class']
                    iref_file = field['ref_file']
                    model_import.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(iref_file))[0], iref_class))
                if typing_list_patter.match(field.get('type', '')):
                    model_import.add("from typing import List")

                if 'type' in field:
                    model_typed_field_list.append('%s: %s = None' % (field['name'], field['type']))
                else:
                    model_typed_field_list.append('%s = None' % field['name'])

                # model_raw_field_list.append(field['name'])
                f_description = '#' + field['description'] if field.get('description') else ''
                lines += "%sself.%s = %s%s%s\n" % (sp8, field['name'], field['name'], sp4, f_description)

            import_rows = '\n'.join(model_import)
            class_row = "class %s(ModelBase):" % (ref_class)
            init_row = "    def __init__(self, %s):" % (', '.join(model_typed_field_list))
            # lines = "".join(["        self.%s = %s\n" % (x, x) for x in model_raw_field_list])
            with open(ref_file, 'w', encoding='utf8') as f:
                f.writelines(import_rows)
                f.writelines('\n' * 3)
                f.writelines(class_row)
                f.writelines('\n')
                f.writelines(init_row)
                f.writelines('\n')
                f.writelines(lines)

    def write_nested_ref(self, root_ref_fields: list):
        for field in root_ref_fields:
            if 'ref' in field:
                imodel_import = {"from easy.base.model_base import ModelBase"}
                iref_class = field['ref_class']
                iref_file = field['ref_file']
                iref_fields = field['ref_fields']
                self.write_nested_ref(iref_fields)  # 递归写嵌套ref_fields
                imodel_typed_field_list = []
                # imodel_raw_field_list = []
                ilines = ""
                for ifield in iref_fields:
                    if 'ref' in ifield:
                        niref_class = ifield['ref_class']
                        niref_file = ifield['ref_file']
                        imodel_import.add("from %s.%s.%s import %s" % (self.project_path_base, self.model_base, os.path.splitext(os.path.basename(niref_file))[0], niref_class))
                    if typing_list_patter.match(ifield.get('type', '')):
                        imodel_import.add("from typing import List")

                    if 'type' in ifield:
                        imodel_typed_field_list.append('%s: %s = None' % (ifield['name'], ifield['type']))
                    else:
                        imodel_typed_field_list.append('%s = None' % ifield['name'])

                    # imodel_raw_field_list.append(ifield['name'])
                    f_description = '#' + field['description'] if field.get('description') else ''
                    ilines += "%sself.%s = %s%s%s\n" % (sp8, ifield['name'], ifield['name'], sp4, f_description)

                iimport_rows = '\n'.join(imodel_import)
                iclass_row = "class %s(ModelBase):" % (iref_class)
                iinit_row = "    def __init__(self, %s):" % (', '.join(imodel_typed_field_list))
                # ilines = "".join(["        self.%s = %s\n" % (x, x) for x in imodel_raw_field_list])
                with open(iref_file, 'w', encoding='utf8') as f:
                    f.writelines(iimport_rows)
                    f.writelines('\n' * 3)
                    f.writelines(iclass_row)
                    f.writelines('\n')
                    f.writelines(iinit_row)
                    f.writelines('\n')
                    f.writelines(ilines)
            else:  # 非model类型直接忽略
                pass

    def get_operator_id(self, operator_id, controller_version):
        operationId = camel_case_to_under_score(operator_id.split('Using')[0])
        version_text = '_' + controller_version if controller_version else ''
        return operationId if operationId.endswith(version_text) else operationId + version_text

    def get_ref_class(self, ref_key):
        if ref_key.find('«') > -1:
            p_start = ref_key.rfind("«") + 1
            p_end = ref_key.find("»")
            ref_class = ref_key[p_start:p_end]
            if ref_class.lower() in ('boolean', 'bool', 'int', 'long', 'string'):  # #/definitions/DataResult«boolean»
                # ref_class = ref_key.replace('«', '').replace('»', '')
                ref_class = (ref_key[:p_start] + ref_class.title() + ref_key[p_end:]).replace('«', '').replace('»', '')
            elif ref_key.find('DataResult') > -1:
                ref_class = 'DataResult' + ref_class
            return ref_class
        else:
            return ref_key

    def build_parameters(self, method):
        params = []
        if method.get('parameters'):
            for param in method['parameters']:
                if param['in'] in ('body'):
                    body = {
                        'in': 'body',
                        'name': param['name']
                    }
                    if '$ref' in param['schema']:
                        ref = param['schema']['$ref']
                        ref_key = ref.lstrip('#/definitions/')
                        ref_class = self.get_ref_class(ref_key)
                        ref_file = self.get_ref_file(ref_class)
                        body['ref'] = ref
                        body['ref_key'] = ref_key
                        body['ref_class'] = ref_class
                        body['type'] = ref_class
                        body['ref_file'] = ref_file
                        body['ref_fields'] = []  # 可能出现嵌套，放在递归中处理
                        self.fill_ref_fields(body, ref_key)
                    elif 'type' in param['schema'] and param['schema']['type'] == 'array':
                        if '$ref' in param['schema']['items']:
                            ref = param['schema']['items']['$ref']
                            ref_key = ref.lstrip('#/definitions/')
                            ref_class = self.get_ref_class(ref_key)
                            ref_file = self.get_ref_file(ref_class)
                            body['ref'] = ref
                            body['ref_key'] = ref_key
                            body['ref_class'] = ref_class
                            body['type'] = 'List[%s]' % ref_class
                            body['ref_file'] = ref_file
                            body['ref_fields'] = []  # 可能出现嵌套，放在递归中处理
                            self.fill_ref_fields(body, ref_key)
                        elif 'type' in param['schema']['items']:
                            type = param['schema']['items']['type']
                            format = param['schema']['items'].get('format')
                            body['type'] = 'List[%s]' % swagger_type_to_python_type(type, format)
                        else:
                            pass
                    elif 'type' in param['schema'] and param['schema']['type'] == 'object':
                        body['type'] = "object"
                    else:  # tbd
                        pass
                    params.append(body)
                elif param['in'] in ('path', 'query'):
                    type = param.get('type')
                    format = param.get('format')
                    params.append({
                        'in': param['in'],
                        'name': param['name'],
                        'type': swagger_type_to_python_type(type, format)
                    })
                else:
                    pass

        return params

    def build_response200(self, method):
        response = {}
        response200 = method['responses']['200']

        if '$ref' in response200['schema']:
            ref = response200['schema']['$ref']
            ref_key = ref.lstrip('#/definitions/')
            ref_class = self.get_ref_class(ref_key)
            ref_file = self.get_ref_file(ref_class)
            response['ref'] = ref
            response['ref_key'] = ref_key
            response['ref_class'] = ref_class
            response['type'] = ref_class
            response['ref_file'] = ref_file
            response['ref_fields'] = []  # 可能出现嵌套，放在递归中处理
            response['description'] = response200.get('description', '')
            self.fill_ref_fields(response, ref_key)
        elif 'type' in response200['schema'] and response200['schema']['type'] == 'string':
            pass

        return response

    # 递归ref - body
    def fill_ref_fields(self, body: dict, ref_key):
        ref = self.service_definitions.get(ref_key)
        properties = ref.get('properties')
        pro_keys = properties.keys()
        for pro_key in pro_keys:
            ibody = {}
            pro = properties[pro_key]
            if '$ref' in pro:
                iref = pro['$ref']
                iref_key = iref.lstrip('#/definitions/')
                # if iref_key == ref_key:
                #     continue  # 跳过自循环
                iref_class = self.get_ref_class(iref_key)
                iref_file = self.get_ref_file(iref_class)
                ibody['name'] = pro_key
                ibody['ref'] = iref
                ibody['ref_key'] = iref_key
                ibody['ref_class'] = iref_class
                ibody['type'] = iref_class
                ibody['ref_file'] = iref_file
                ibody['ref_fields'] = []
                if iref_key != ref_key:  # 跳过自循环
                    self.fill_ref_fields(ibody, iref_key)
                body['ref_fields'].append(ibody)
            elif 'type' in pro and pro['type'] == 'array':
                if '$ref' in pro['items']:
                    iref = pro['items']['$ref']
                    iref_key = iref.lstrip('#/definitions/')
                    # if iref_key == ref_key:
                    #     continue  # 跳过自循环
                    iref_class = self.get_ref_class(iref_key)
                    iref_file = self.get_ref_file(iref_class)
                    ibody['name'] = pro_key
                    ibody['description'] = pro.get('description')
                    ibody['ref'] = iref
                    ibody['ref_key'] = iref_key
                    ibody['ref_class'] = iref_class
                    ibody['type'] = 'List[%s]' % iref_class
                    ibody['ref_file'] = iref_file
                    ibody['ref_fields'] = []
                    if iref_key != ref_key:  # 跳过自循环
                        self.fill_ref_fields(ibody, iref_key)
                    body['ref_fields'].append(ibody)
                else:
                    type = pro['items']['type']
                    format = pro['items'].get('format')
                    ibody['name'] = pro_key
                    ibody['type'] = 'List[%s]' % swagger_type_to_python_type(type, format)
                    ibody['description'] = pro.get('description', '')
                    body['ref_fields'].append(ibody)
            else:
                type = pro['type']
                format = pro.get('format')
                ibody['name'] = pro_key
                ibody['type'] = swagger_type_to_python_type(type, format)
                ibody['description'] = pro.get('description', '')
                body['ref_fields'].append(ibody)

    def get_ref_file(self, ref_class):
        ref_file_prefix = camel_case_to_under_score(ref_class)
        ref_file_base = ref_file_prefix + '.py'
        ref_file = os.path.join(self.model_base, ref_file_base)
        if ref_file not in self.ref_real_file:
            if not os.path.exists(ref_file):
                self.ref_real_file[ref_file] = ref_file
            else:
                ref_file_base = ref_file_prefix + '%s.py' % self.stamp
                self.ref_real_file[ref_file] = os.path.join(self.model_base, ref_file_base)

        return ref_file


def __get_run_args():
    arg_parser = argparse.ArgumentParser('')
    arg_parser.add_argument('-A', '--swagger-doc', action='store', dest='swagger_doc', help='swagger json文档url地址,如: http://app.com/v2/api-docs')
    arg_parser.add_argument('-B', '--code-base', action='store', dest='code_base', help='生成代码目标目录')
    arg_parser.add_argument('-M', '--model-base', action='store', dest='model_base', default='model', help='model目标目录')
    arg_parser.add_argument('-C', '--controller-base', action='store', dest='controller_base', default='controller', help='controller目标目录')
    arg_parser.add_argument('-S', '--service-base', action='store', dest='service_base', default='service', help='service目标目录')
    arg_parser.add_argument('-P', '--included-paths', action='store', nargs='+', dest='included_paths', help='待处理的接口列表,不填写则处理全部')
    arg_parser.add_argument('-E', '--excluded-paths', action='store', nargs='+', dest='excluded_paths', help='排除的待处理接口列表')
    arg_parser.add_argument('-K', '--keep', action='store', type=bool, dest='keep', default=True, help='是否保留老版本，默认为True')

    args = arg_parser.parse_args()

    args.code_base = os.getcwd() if not args.code_base else args.code_base

    assert os.path.split(args.code_base)[-2].endswith('autotest')
    args.project_path_base = 'autotest.' + os.path.split(args.code_base)[-1]

    config_file = os.path.join(args.code_base, 'pycodegenconfig.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            config: dict = json.load(f)
            args.swagger_doc = config['swagger_doc'] if not args.swagger_doc and 'swagger_doc' in config else args.swagger_doc
            args.model_base = config['model_base'] if not args.model_base and 'model_base' in config else args.model_base
            args.controller_base = config['controller_base'] if not args.controller_base and config.get('controller_base') else args.controller_base
            args.service_base = config['service_base'] if not args.service_base and config.get('service_base') else args.service_base
            args.included_paths = config['included_paths'] if not args.included_paths and config.get('included_paths') else args.included_paths
            args.excluded_paths = config['excluded_paths'] if not args.excluded_paths and config.get('excluded_paths') else args.excluded_paths

    return args


def main():
    args = __get_run_args()
    pycodegen = PyCodeGen(args=args)
    pycodegen.run()


if __name__ == '__main__':
    main()
