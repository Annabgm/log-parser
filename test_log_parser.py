import unittest
from log_analyzer import (
define_conf_params,
last_log_finder,
parse_file,
calculate_stats
)

config = {
    "REPORT_SIZE": 2,
    "REPORT_DIR": ".",
    "LOG_DIR": "."
}

class LogParserTest(unittest.TestCase):

    def test_conf_params_fail(self):
        self.assertRaises(FileNotFoundError, define_conf_params, './source/default.json')

    def test_conf_params_fail2(self):
        try:
            define_conf_params('./source/config_u2.yaml')
        except :
            pass
        else:
            self.fail('Fail to recognize wrong config file format')

    def test_conf_params_collision(self):
        size, report_dir, log_dir = define_conf_params('./source/config_u1.json')
        self.assertEqual(size, 1000)
        self.assertEqual(report_dir, './reports')
        self.assertEqual(log_dir, '.')

    def test_last_log_finder(self):
        ls = ['nginx-access-ui.log-20170630.gz',
              'nginx-access-ui.log-20170730.bz',
              'nginx-access-ui.log-20170830']
        last_log1, last_log2 = last_log_finder(ls)
        self.assertEqual(last_log1, 'nginx-access-ui.log-20170830')
        self.assertEqual(last_log2, '20170830')

    def test_parse_file(self):
        ls = ['1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/?server_name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133',
              '1.169.137.128 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/16852664 HTTP/1.1" 200 19415 "-" "Slotovod" "-" "1498697422-2118016444-4708-9752769" "712e90144abee9" 0.199']
        lines = (i for i in ls)
        result_dict = parse_file(lines)
        self.assertEqual(result_dict, {'/api/1/?server_name=WIN7RB4': [0.133],
                                           '/api/v2/banner/16852664': [0.199]})

    def test_parse_file_fail(self):
        ls = ['[29/Jun/2017:03:50:22 +0300] 0.133',
              '[29/Jun/2017:03:50:22 +0300] 0.199']
        lines = (i for i in ls)
        result_dict = parse_file(lines)
        self.assertIsNone(result_dict)

    def test_calculate_stats(self):
        log_dict = {'/api/1/?server_name=WIN7RB4': [0.1, 0.2, 0.3],
                    '/api/v2/banner/16852664': [0.1, 0.1, 0.1, 0.1]}
        result = calculate_stats(log_dict)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1].url, '/api/v2/banner/16852664')
        self.assertEqual(result[1].count, 4)
        self.assertAlmostEqual(result[1].count_perc, round(4/7, 3))
        self.assertAlmostEqual(result[1].time_sum, 0.4)
        self.assertAlmostEqual(result[1].time_perc, round(0.4/1.0, 3))
        self.assertAlmostEqual(result[1].time_avg, 0.1)
        self.assertAlmostEqual(result[1].time_max, 0.1)
        self.assertAlmostEqual(result[1].time_med, 0.1)


if __name__ == '__main__':
    unittest.main()