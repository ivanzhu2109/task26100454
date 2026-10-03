"""召回范围计算的自动化测试。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from recall_scope import LedgerStore, compute_recall


class RecallTestBase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.store = LedgerStore(self.db_path)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def recall(self, suspicious, cutoff):
        return compute_recall(self.store.load_upto(cutoff), set(suspicious))

    def reopen(self):
        self.store.close()
        self.store = LedgerStore(self.db_path)


class TestBackflowAndClear(RecallTestBase):
    """回流、部分领用、清空再补货；验证多个截止点。"""

    def setUp(self):
        super().setUp()
        s = self.store
        s.append_inbound("W1", 10)      # 1  正常入库
        s.append_issue("W1", 2)         # 2  污染到达前离开，永不召回
        s.append_inbound("W1", 5)       # 3  可疑入库 -> W1 全部(13)疑似
        s.append_transfer("W1", "S1", 5)  # 4  S1 变疑似；W1 剩 8 仍疑似
        s.append_issue("S1", 2)         # 5  疑似领用，召回
        s.append_transfer("S1", "W1", 3)  # 6  回流：S1 清空解除，W1 仍疑似
        s.append_issue("W1", 11)        # 7  疑似领用，召回；W1 清空解除
        s.append_inbound("W1", 6)       # 8  清空后正常补货，不继承旧状态
        s.append_issue("W1", 4)         # 9  正常领用，不召回
        self.cutoff_final = 9

    def test_cutoff_before_contamination(self):
        r = self.recall(suspicious={3}, cutoff=2)
        self.assertEqual(r.recalled_issues, [])
        self.assertEqual(r.suspect_stock, {})

    def test_cutoff_mid_chain(self):
        r = self.recall(suspicious={3}, cutoff=5)
        self.assertEqual([(i.seq, i.qty) for i in r.recalled_issues], [(5, 2)])
        self.assertEqual(r.suspect_stock, {"W1": 8, "S1": 3})

    def test_cutoff_after_backflow(self):
        r = self.recall(suspicious={3}, cutoff=6)
        self.assertEqual([(i.seq, i.qty) for i in r.recalled_issues], [(5, 2)])
        self.assertEqual(r.suspect_stock, {"W1": 11})

    def test_final_cleared_and_restocked(self):
        r = self.recall(suspicious={3}, cutoff=self.cutoff_final)
        self.assertEqual(
            [(i.seq, i.qty) for i in r.recalled_issues], [(5, 2), (7, 11)])
        self.assertEqual(r.suspect_stock, {})

    def test_reopen_consistent(self):
        before = self.recall(suspicious={3}, cutoff=self.cutoff_final)
        self.reopen()
        after = self.recall(suspicious={3}, cutoff=self.cutoff_final)
        self.assertEqual(before.recalled_issues, after.recalled_issues)
        self.assertEqual(before.suspect_stock, after.suspect_stock)


class TestMergeDownstream(RecallTestBase):
    """多笔可疑入库在下游汇合，领用与库存只计一次。"""

    def setUp(self):
        super().setUp()
        s = self.store
        s.append_inbound("A", 5)        # 1 可疑
        s.append_inbound("B", 7)        # 2 可疑
        s.append_transfer("A", "C", 5)  # 3 A 清空解除，C 疑似
        s.append_transfer("B", "C", 7)  # 4 B 清空解除，C 汇合 12 疑似
        s.append_issue("C", 4)          # 5 疑似领用，只计一次
        s.append_inbound("C", 3)        # 6 正常入库混入疑似容器

    def test_union_no_double_count(self):
        r = self.recall(suspicious={1, 2}, cutoff=6)
        self.assertEqual([(i.seq, i.container, i.qty) for i in r.recalled_issues],
                         [(5, "C", 4)])
        self.assertEqual(r.suspect_stock, {"C": 11})

    def test_single_suspicious_subset(self):
        r = self.recall(suspicious={2}, cutoff=6)
        self.assertEqual([(i.seq, i.qty) for i in r.recalled_issues], [(5, 4)])
        self.assertEqual(r.suspect_stock, {"C": 11})

    def test_reopen_consistent(self):
        before = self.recall(suspicious={1, 2}, cutoff=6)
        self.reopen()
        after = self.recall(suspicious={1, 2}, cutoff=6)
        self.assertEqual(before.recalled_issues, after.recalled_issues)
        self.assertEqual(before.suspect_stock, after.suspect_stock)


if __name__ == "__main__":
    unittest.main()
