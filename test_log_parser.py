import unittest
import copy

from log_analyzer import (
define_conf_params,
calculate_stats,
config
)

config_file = copy.deepcopy(config)

class LogParserTest(unittest.TestCase):

    def test_conf_params_fail(self):
        self.assertRaises(Exception, define_conf_params, './config/default.json')

    def test_conf_params_fail2(self):
        try:
            define_conf_params(config_file, './config/config_u2.yaml')
        except :
            pass
        else:
            self.fail('Fail to recognize wrong config file format')

    def test_conf_params_collision(self):
        config = define_conf_params(config_file, './config/config_u1.json')
        self.assertEqual(config['REPORT_SIZE'], 1000)
        self.assertEqual(config['REPORT_DIR'], './reports')
        self.assertEqual(config['LOG_DIR'], '.')

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