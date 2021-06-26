#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime
import gzip
from collections import defaultdict, OrderedDict, namedtuple
from statistics import median
from operator import attrgetter
from string import Template
import argparse
import json
import logging
import re


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

parser = argparse.ArgumentParser('Logs parser')
parser.add_argument('--config', default='default.json', help='file to read the config from')
AGRS = parser.parse_args()

Stats = namedtuple('Stats', [
    'url',
    'count',
    'count_perc',
    'time_sum',
    'time_perc',
    'time_avg',
    'time_max',
    'time_med'
])


def define_conf_params(user_conf):
    """
    function read config file and cobain default and new parameter
    :param user_conf:
    :return: tuple(int, str, str)
    """
    try:
        with open(user_conf, 'r') as f:
            config_user = json.load(f)
    except FileNotFoundError:
        print('Config file {} is not found'.format(user_conf))
        raise
    except:
        print('Config file {} cannot be parsed'.format(user_conf))
        raise
    else:
        report_size = config_user['REPORT_SIZE'] if 'REPORT_SIZE' in config_user.keys() else config['REPORT_SIZE']
        report_dir = config_user['REPORT_DIR'] if 'REPORT_DIR' in config_user.keys() else config['REPORT_DIR']
        log_dir = config_user['LOG_DIR'] if 'LOG_DIR' in config_user.keys() else config['LOG_DIR']
        return report_size, report_dir, log_dir


def last_log_finder(files_list_ui):
    """
    function search in files to find the latest log
    :return: tuple[str, str]
    """
    files_tuple_ui = [(i, i.split('-')[-1].split('.')[0]) for i in files_list_ui]
    files_tuple_ui.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y%m%d'))
    return files_tuple_ui[-1]


def get_open(name):
    """
    function read file and define generator for following line parcing
    :param name: str
    :return: itarable
    """
    if name.endswith('.gz'):
        fin = gzip.open(name, 'rb')
    else:
        fin = open(name, 'rb')
    log_gen = (row.decode('utf-8') for row in fin)
    return log_gen, fin


def parse_file(lines):
    """
    from lines generate dict with keys - url and values - all find request times for the url
    :param lines: generator
    :return: dict[str, list[float]]
    """
    logpats = r"""(\S+) (\S+)  (\S+) (\S+) (\S+) "(\S+) (\S+) (\S+)" (\S+) (\S+) "(\S+)" "(\S+).*?" "(\S+)" "(\S+)" "(\S+)" (\S+)"""
    logpat = re.compile(logpats)

    groups = (logpat.match(line) for line in lines)
    url_dict = defaultdict(list)
    count = 0
    er_count = 0
    for g in groups:
        count += 1
        if g is None:
            er_count += 1
        else:
            row = g.groups()
            url_dict[row[6]].append(float(row[-1]))
    fail_percent = er_count/count
    logging.info('Percent rate of parsing failure is {}'.format(fail_percent))
    if fail_percent > 0.8:
        return None
    else:
        return url_dict

def calculate_stats(parse_dict):
    """
    function calculate statistics on values of dict
    :param parse_dict: dict[str, list[float]]
    :return: list[Stats]
    """
    count_tot = sum([len(i) for i in parse_dict.values()])
    time_tot = sum([sum(i) for i in parse_dict.values()])
    report = []
    for k, v in parse_dict.items():
        report.append(Stats(
            url=k,
            count=len(v),
            count_perc=round(len(v)/count_tot, 3),
            time_sum=sum(v),
            time_perc=round(sum(v)/time_tot, 3),
            time_avg=round(sum(v)/len(v),3),
            time_max=max(v),
            time_med=median(v)))
    return report

def save_html(res, new_name):
    """
    function replace default name in html-template by json table and write in file new_name
    :param res: list[Stats]
    :param new_name: str
    :return:
    """
    html_templ = open('report.html', 'r', encoding='utf-8')
    templ = Template(html_templ.read()).safe_substitute(table_json=res)
    result_new = open(new_name, 'w')
    result_new.write(templ)
    result_new.close()


def main():
    size, report_dir, log_dir = define_conf_params(AGRS.config)
    logging.basicConfig(
        filename=os.path.join(log_dir, 'log_parser.log') or None,
        level=logging.INFO,
        datefmt='%Y.%m.%d %H:%M:%S',
        format='[%(asctime)s] %(levelname).1s %(message)s',
        filemode='w')
    logging.info('Config parameters: report_size={0}, report_dir={1}, log_dir={2}'.format(size, report_dir, log_dir))

    try:
        logname = r'nginx-access-ui\.log-\d{8}[.]?[g]?[z]?'
        lognames = re.compile(logname)
        files_list_ui = [i for i in os.listdir(log_dir) if lognames.fullmatch(i)]
        if files_list_ui:
            target_file, target_date = last_log_finder(files_list_ui)
            logging.info('Last log file name is {}'.format(target_file))
            report_file = 'report-{}.html'.format(target_date.replace('-', '.'))
            if report_file not in os.listdir(report_dir):
                lines, f = get_open(os.path.join(log_dir, target_file))
                url_data = parse_file(lines)
                f.close()
                if url_data is not None:
                    report_data = calculate_stats(url_data)
                    report_data = sorted(report_data, key=attrgetter('time_sum'), reverse=True)
                    res = [dict(i._asdict()) for i in report_data[:size]]
                    logging.info('Report is in {} file'.format(report_file))
                    save_html(res, os.path.join(report_dir, report_file))
                else:
                    logging.info('Parsing error exceed critical level 80%')
        else:
            logging.info('No log files in {} directory'.format(log_dir))
    except Exception as exception:
        logging.exception(exception)



if __name__ == "__main__":
    main()
