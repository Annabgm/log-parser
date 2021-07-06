#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime
import gzip
from collections import defaultdict, namedtuple
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
    :return: dict(str, union(str, int))
    """
    try:
        with open(user_conf, 'r') as f:
            config_user = json.load(f)
    except:
        print('Config file {} cannot be parsed'.format(user_conf))
        raise
    config.update(config_user)
    return config


def log_finder(log_dir):
    """
    function search in directory the latest file what matches the name
    :return: tuple[str, str] or None
    """
    logname = r'nginx-access-ui\.log-\d{8}[.]?[g]?[z]?'
    lognames = re.compile(logname)
    files_list_ui = [i for i in os.listdir(log_dir) if lognames.fullmatch(i)]
    files_tuple_ui = [(i, i.split('-')[-1].split('.')[0]) for i in files_list_ui]
    files_tuple_ui.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y%m%d'))
    return files_tuple_ui[-1]


def parse_file(name):
    """
    function read file and parcing to indivudual events what matches pattern
    :param name: str
    :return: dict[str, list(float)]
    """
    if name.endswith('.gz'):
        fin = gzip.open(name, 'rb')
    else:
        fin = open(name, 'rb')
    log_gen = (row.decode('utf-8') for row in fin)

    logpats = r"""(\S+) (\S+)  (\S+) (\S+) (\S+) "(\S+) (\S+) (\S+)" (\S+) (\S+) "(\S+)" "(\S+).*?" "(\S+)" "(\S+)" "(\S+)" (\S+)"""
    logpat = re.compile(logpats)

    groups = (logpat.match(line) for line in log_gen)
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
    fin.close()
    fail_percent = er_count/count
    logging.info('Percent rate of parsing failure is {}'.format(fail_percent))
    if fail_percent > 0.8:
        raise Exception('Percent rate of parsing failure is {}'.format(fail_percent))
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
            time_avg=round(sum(v)/len(v), 3),
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
    with open('report.html', 'r', encoding='utf-8') as tmp:
        templ = Template(tmp.read()).safe_substitute(table_json=res)
    with open(new_name, 'w') as f:
        f.write(templ)


def main(arg):
    config_file = define_conf_params(arg.config)
    logging.info('Config parameters: '.format(config_file))
    target_file = None
    try:
        target_file = log_finder(config_file['LOG_DIR'])
    except:
        logging.info('No log files in {} directory'.format(config_file['LOG_DIR']))
        pass

    if target_file is not None:
        logging.info('Last log file name is {}'.format(target_file[0]))
        report_date = datetime.datetime.strptime(target_file[1], '%Y%m%d').strftime('%Y.%m.%d')
        report_file = 'report-{}.html'.format(report_date)
        if not os.path.exists(os.path.join(config_file['REPORT_DIR'], report_file)):
            try:
                url_data = parse_file(os.path.join(config_file['LOG_DIR'], target_file[0]))
                report_data = calculate_stats(url_data)
                report_data = sorted(report_data, key=attrgetter('time_sum'), reverse=True)
                res = [dict(i._asdict()) for i in report_data[:config_file['REPORT_SIZE']]]
                logging.info('Report is in {} file'.format(report_file))
                save_html(res, os.path.join(config_file['REPORT_DIR'], report_file))
            except Exception as e:
                logging.info('Parsing error {}'.format(e))
        else:
            logging.info('{0} file already in {1} directory'.format(report_file, config_file['REPORT_DIR']))


if __name__ == "__main__":
    parser = argparse.ArgumentParser('Logs parser')
    parser.add_argument('--config', default='default.json', help='file to read the config from')
    arg = parser.parse_args()
    logging.basicConfig(
        filename=os.path.join(config['LOG_DIR'], 'log_parser.log') or None,
        level=logging.INFO,
        datefmt='%Y.%m.%d %H:%M:%S',
        format='[%(asctime)s] %(levelname).1s %(message)s',
        filemode='w')
    try:
        main(arg)
    except Exception as exception:
        logging.exception("Unexpected error: {}".format(exception))
