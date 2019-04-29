import os
import shutil
import logging
import pytest
from datetime import datetime
from easy.utils.dateUtil import FMT


def pytest_addoption(parser):
    group_run = parser.getgroup('run settings', '执行配置')
    group_run.addoption('-E', '--env', dest='env', default='qa', help='自动化运行环境, qa,qa1,qa2..., default: qa')
    group_run.addoption('--report-keep', action='store', dest='max_keep', type=int, default=5,
                        help='specific number of old reports to keep under .pytest_cache directory, default keep: 5.')


@pytest.fixture(scope="session", autouse=True)
def backup_html_report(request):
    """
    按设定数量max_keep备份report到.pytest_cache目录下
    :return:
    """
    report_file = r'report.html'
    dest_dir = r'.pytest_cache/reportbackup'
    max_keep = request.config.option.max_keep
    if os.path.exists(report_file):
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=False)
        report_time = os.path.getmtime(report_file)
        report_file_backup = os.path.join(dest_dir, 'report_%s.html' % datetime.fromtimestamp(report_time).strftime(FMT.DATE_TIME))
        shutil.move(report_file, report_file_backup)

        all_reports = [(os.path.join(dest_dir, f), os.path.getmtime(os.path.join(dest_dir, f))) for f in os.listdir(dest_dir)]
        all_reports.sort(key=lambda t: t[1])
        for report in all_reports[:-max_keep]:
            try:
                os.remove(report[0])
            except Exception as e:
                logging.warning('过期report删除失败[超过%s个, 异常信息:%s]' % (max_keep, e))
