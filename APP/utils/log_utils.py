import logging
import os
from logging.handlers import TimedRotatingFileHandler
import sys

class Logger(object):
    def __init__(self, name=__name__, log_file=None, level=logging.INFO, stream=True):
        """
        初始化日志模块
        :param name: 模块名称
        :param log_file: 日志文件路径，如果不指定则输出到控制台
        :param level: 日志级别，默认INFO
        :param stream: 是否输出到控制台，默认True
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        if log_file:
            # 如果日志文件所在目录不存在，则创建目录
            if not os.path.exists(os.path.dirname(log_file)):
                os.makedirs(os.path.dirname(log_file))
            # 设置日志回滚，例如每天生成一个新的日志文件，最多保留7天的日志
            handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7,encoding='utf-8')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        if stream:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        """返回配置好的logger实例"""
        return self.logger