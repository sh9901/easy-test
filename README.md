# 使用说明

## 基础类使用说明
### mode_base.py::ModelBase
可以用做Python对象的基类, 用于被model类继承, 或者json反序列化时使用
以model对象的形式与被测应用的请求/返回进行交互
实现了json(),to_model()方法,重写了__eq__方法
方法说明:
* 新增json()方法, 返回json格式的属性k/v对象
* 新增str()方法, 返回json格式的str对象
* 新增to_model()方法,用于json反序列化为Python 
* 新增mix_body()方法, 对象为分页请求或返回时, 可以把数据对象嵌入到模板中
* 重写__eq__()方法,根据model.json()的值进行精确比对  
 ```python
    jsonUtil.compare(self_dict, other_dict, ignore_nones=False, unify_name=False, 
        match_type=jsonUtil.MatchType.ExactMatch, contains_as_true=False, user_defined_match_func=None)
```

### service_base.py::ServiceBase
ServiceBase是本类库的核心, 在requests库的基础上进行封装并在保持原api功能和请求方式的基础上增加了灵活的hook功能
>为什么不使用requests自带的hook参数  
>+ requests hooks不支持hook自定义参数
>+ requests hooks不支持插入通用hook在不合适时候unhook   

使用方式:
>ServiceBase类应该被Controller继承, 并由controller通过ServiceBase发起requests调用
ServiceBase的构造函数包含host,vpath,hook_funcs三个参数
>* host: 被测应用的域名, 必填
>* vpath: Controller的base地址, 非必填
>* hook_funcs: hook functiton列表, 每个hook也要以列表的形式提供, 如:[[fun1,arg1],[func2,arg2]], 非必填 
>* ~~json_return[removed]: 是否返回resp.json(),默认为False, 非必填~~ 

>Controller需要重写父类的__int__方法并提供host参数, 可选参数根据使用场景决定

>ServiceBase包装了requests的get/post/put/delete等http方法, 并新增了load,hook_funcs[H],model_hook[M],
info四个参数
>* load: 请求作为model转入使用这个参数, 推荐使用
>* hook_funcs: 可以补充或禁用__init__中指定的hooks
>>* 新增ServiceBase初始化时没有加入的hooks
>>* hook最后一个参数为ignore则如果加入的hook列表中有同名方法(不管参数是否相同)则跳过执行
>>* hook最后一个参数为xignore则仅hook列表中有同名方法(且参数相同)则跳过执行
>>* 如果hook重复添加且参数相同,仅执行一次
>* model_hook: 指定将response.json()反序列化为model的方法
>* info:日志记录用户输入信息

### service_base_hooks.py
预置的hooks和示例, 任何有效的model方法,module方法,类静态方法,类示例方法  
唯一要求:方法第一个参数为requests.model.Response对象



## utils使用说明

### dateUtil.py (略)

### jsonUtil.py
json工具类
* 打印及格式化方法
* Default类, 用于DB使用DictCursor查询结果的model反序列化
* json比较相关   
```python
def compare(actual: dict, expected: dict, ignore_nones=False, unify_name=False, match_type=MatchType.ExactMatch, contains_as_true=True, user_defined_match_func=None) -> bool:
    """
    json/dict比对
    :param actual:
    :param expected:
    :param ignore_nones:
    :param unify_name:     if unify_name:  # 为了解决crm_sale_id和crmSaleId无法匹配的问题, 统一处理为CRMSALEID
    :param match_type: MatchType(RegexMatch/ExactMatch)枚举,传入1,True等可判为True的字段都作为ExactMatch处理,其它如0,FALSE则作为RegexMatch,,枚举类型保留扩展
    :param contains_as_true: 期望值包含于实际值则认为匹配, 用于支持仅比对部分字段
    :param user_defined_match_func: 提供给用户自定义比较方式的插入点, 如果提供则只根据参数处理ignore_nones/unify_name, 而不执行内置的比对逻辑,该方法期望返回bool型结果
    :return: bool
    """
```

### MSSqlDb.py - MSSQL Python查询包装

### MySQLdb.py.py - MySQL Python查询包装

### peewee_custom.py - peewee自定义数据类型

### randomUtil - 随机字符串/数字工具

### sqlite3_base.py - 类似于redis作用的本地k/v缓存

### pytest-salt - pytest plugin
    用于指定测试执行环境和自动备份测试报告