import unittest
from parlay_probability import wilson_interval, joint_bounds, yes_break_even, yes_expected_value

class ProbabilityMathTests(unittest.TestCase):
    def test_wilson_interval(self):
        lo, hi = wilson_interval(8, 10)
        self.assertLess(lo, .8)
        self.assertGreater(hi, .8)
        self.assertIsNone(wilson_interval(11, 10))
        self.assertIsNone(wilson_interval(0, 0))

    def test_joint_bounds_allow_dependence(self):
        self.assertEqual(joint_bounds([.8, .7]), (.5, .7))
        self.assertEqual(joint_bounds([.2, .3, .4]), (0.0, .2))
        self.assertIsNone(joint_bounds([1.2, .5]))

    def test_price_and_fees(self):
        self.assertAlmostEqual(yes_break_even(.62, .02), .64)
        self.assertAlmostEqual(yes_expected_value(.7, .62, .02), .06)
        self.assertIsNone(yes_expected_value(.7, .99, .02))

if __name__ == "__main__":
    unittest.main()
