import os
import tempfile
import unittest

from recall import RecallLedger


class RecallTestBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "ledger.db")
        self.ledger = RecallLedger(self.db)

    def tearDown(self):
        self.ledger.close()


class TestBackflowAndRestock(RecallTestBase):
    """疑似物料在两个容器间回流、部分领用、最终清空再补货。"""

    def setUp(self):
        super().setUp()
        lg = self.ledger
        self.s1 = lg.append_inbound("A", 10)   # 正常入库
        self.s2 = lg.append_consume("A", 3)    # 污染到达前离开，不召回
        self.s3 = lg.append_inbound("A", 5)    # 可疑入库，A 全部 12 疑似
        self.s4 = lg.append_transfer("A", "B", 6)  # A=6 疑似, B=6 疑似
        self.s5 = lg.append_consume("B", 2)    # 疑似领用，召回；B=4 疑似
        self.s6 = lg.append_transfer("B", "A", 4)  # 回流，B 清零状态消失；A=10 疑似
        self.s7 = lg.append_consume("A", 4)    # 召回；A=6 疑似
        self.s8 = lg.append_consume("A", 6)    # 召回；A 清零状态消失
        self.s9 = lg.append_inbound("A", 8)    # 清空后正常补货，不继承旧状态
        self.s10 = lg.append_consume("A", 3)   # 正常领用，不召回
        self.s11 = lg.append_transfer("A", "B", 2)  # 正常转移，不产生疑似

    def test_cutoff_before_contamination(self):
        r = self.ledger.recall([self.s3], self.s2)
        self.assertEqual(r.recalled_consumes, [])
        self.assertEqual(r.suspect_stock, {})

    def test_cutoff_mid_propagation(self):
        r = self.ledger.recall([self.s3], self.s5)
        self.assertEqual(r.recalled_consumes, [(self.s5, 2)])
        self.assertEqual(r.suspect_stock, {"A": 6, "B": 4})

    def test_cutoff_after_empty(self):
        r = self.ledger.recall([self.s3], self.s8)
        self.assertEqual(
            r.recalled_consumes,
            [(self.s5, 2), (self.s7, 4), (self.s8, 6)],
        )
        self.assertEqual(r.suspect_stock, {})

    def test_cutoff_after_restock(self):
        # 清空后补货与后续领用不影响召回清单；之后的流水不影响本次结果
        r = self.ledger.recall([self.s3], self.s11)
        self.assertEqual(
            r.recalled_consumes,
            [(self.s5, 2), (self.s7, 4), (self.s8, 6)],
        )
        self.assertEqual(r.suspect_stock, {})

    def test_pre_contamination_consume_not_recalled(self):
        # 污染到达前已离开的物料不倒推
        for cutoff in (self.s2, self.s5, self.s8, self.s11):
            seqs = [s for s, _ in self.ledger.recall([self.s3], cutoff).recalled_consumes]
            self.assertNotIn(self.s2, seqs)
            self.assertNotIn(self.s10, seqs)

    def test_reopen_consistency(self):
        before = self.ledger.recall([self.s3], self.s11)
        self.ledger.close()
        self.ledger = RecallLedger(self.db)
        after = self.ledger.recall([self.s3], self.s11)
        self.assertEqual(before.recalled_consumes, after.recalled_consumes)
        self.assertEqual(before.suspect_stock, after.suspect_stock)


class TestConvergingSuspiciousInbounds(RecallTestBase):
    """多笔可疑入库在下游汇合，领用及剩余库存只计一次。"""

    def setUp(self):
        super().setUp()
        lg = self.ledger
        self.s1 = lg.append_inbound("A", 5)    # 可疑
        self.s2 = lg.append_inbound("B", 7)    # 可疑
        self.s3 = lg.append_transfer("A", "C", 5)  # C=5 疑似
        self.s4 = lg.append_transfer("B", "C", 7)  # 汇合，C=12 疑似
        self.s5 = lg.append_consume("C", 4)    # 召回一次；C=8 疑似
        self.s6 = lg.append_transfer("C", "D", 3)  # D=3 疑似，C=5 疑似

    def test_union_counted_once(self):
        r = self.ledger.recall([self.s1, self.s2], self.s6)
        self.assertEqual(r.recalled_consumes, [(self.s5, 4)])
        self.assertEqual(r.suspect_stock, {"C": 5, "D": 3})

    def test_single_suspicious_path(self):
        # 只标记其中一笔可疑入库时，传播路径仍覆盖汇合点下游
        r = self.ledger.recall([self.s1], self.s6)
        self.assertEqual(r.recalled_consumes, [(self.s5, 4)])
        self.assertEqual(r.suspect_stock, {"C": 5, "D": 3})

    def test_cutoff_before_convergence(self):
        r = self.ledger.recall([self.s1, self.s2], self.s3)
        self.assertEqual(r.recalled_consumes, [])
        self.assertEqual(r.suspect_stock, {"B": 7, "C": 5})

    def test_reopen_consistency(self):
        before = self.ledger.recall([self.s1, self.s2], self.s6)
        self.ledger.close()
        self.ledger = RecallLedger(self.db)
        after = self.ledger.recall([self.s1, self.s2], self.s6)
        self.assertEqual(before.recalled_consumes, after.recalled_consumes)
        self.assertEqual(before.suspect_stock, after.suspect_stock)


if __name__ == "__main__":
    unittest.main()
