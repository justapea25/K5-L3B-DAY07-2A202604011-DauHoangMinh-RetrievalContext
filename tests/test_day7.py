"""Offline tests for Day 7 code (no DB, no API). Fakes here test control flow only, never quality."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import Agent, Context  # noqa: E402
from src.common import chunk_hits_evidence, groups_covered  # noqa: E402
from src.retrievers import BM25Retriever, HybridRetriever, tokenize  # noqa: E402


def chunk(i, text, pages=(1,), chapter="I"):
    return {"id": i, "text": text, "source_id": "doc", "source": "s", "page": pages[0],
            "metadata": {"pages": list(pages), "chapter": chapter}}


CHUNKS = [chunk("a", "Thời gian thử việc không quá 60 ngày", chapter="III"),
          chunk("b", "Giờ làm việc ban đêm được tính từ 22 giờ", (2, 3), "VII"),
          chunk("c", "Người lao động được nghỉ Tết Âm lịch 05 ngày", chapter="VII")]


class EvidenceTest(unittest.TestCase):
    def test_hit_uses_all_covered_pages_and_whitespace_norm(self):
        ev = {"source_id": "doc", "page": 3, "evidence": "tính từ  22\ngiờ"}
        self.assertTrue(chunk_hits_evidence(CHUNKS[1], ev))
        self.assertFalse(chunk_hits_evidence(CHUNKS[1], {**ev, "page": 4}))

    def test_groups_require_each_group(self):
        g = [[{"source_id": "doc", "page": 1, "evidence": "60 ngày"}],
             [{"source_id": "doc", "page": 2, "evidence": "22 giờ"}]]
        self.assertEqual(groups_covered(CHUNKS[:1], g), [True, False])
        self.assertEqual(groups_covered(CHUNKS[:2], g), [True, True])


class BM25Test(unittest.TestCase):
    def test_bigrams_and_filter(self):
        self.assertIn("thử_việc", tokenize("Thử việc", bigrams=True))
        r = BM25Retriever(CHUNKS)
        self.assertEqual(r.search("thử việc bao lâu", top_k=1)[0]["id"], "a")
        self.assertEqual(r.search("thử", top_k=3, filters={"chapter": "VII"}), [])
        self.assertEqual(r.search("thử", top_k=3, filters={"chapter": "III"})[0]["id"], "a")
        with self.assertRaises(ValueError):
            r.search("x", filters={"page": 1})

    def test_rrf_fuses_ranks(self):
        class Fixed:
            def __init__(self, ids, name): self.ids, self.name = ids, name
            def search(self, q, top_k, filters=None):
                return [{**next(c for c in CHUNKS if c["id"] == i), "score": 1.0, "rank": k + 1,
                         "method": self.name} for k, i in enumerate(self.ids[:top_k])]
            def info(self): return {}
        h = HybridRetriever(Fixed(["a", "b"], "dense"), Fixed(["b", "c"], "bm25"))
        out = h.search("q", top_k=3)
        self.assertEqual(out[0]["id"], "b")  # in both lists
        self.assertEqual(out[0]["component_ranks"], {"dense": 2, "bm25": 1})


class ContextTest(unittest.TestCase):
    def test_budget_and_policies(self):
        big = chunk("big", "x" * 300)
        small = chunk("small", "y" * 50)
        res1 = [{**big, "rank": 2}, {**CHUNKS[0], "rank": 1}]
        res2 = [{**small, "rank": 1}]
        blk = Context(1).block
        budget = len(blk(big)) + len(blk(CHUNKS[0])) + 4
        fc = Context(budget, "first_come"); fc.add(res1, 1); fc.add(res2, 2)
        self.assertNotIn("small", fc.ids)           # earlier chunks keep their place
        br = Context(budget, "best_rank"); br.add(res1, 1); br.add(res2, 2)
        self.assertEqual(set(br.ids), {"a", "small"})  # rank-1 chunks of both searches win


def tool_call(name, args):
    fn = SimpleNamespace(name=name, arguments=json.dumps(args, ensure_ascii=False))
    msg = SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id=f"c{name}", function=fn)])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                           usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10))


class FakeClient:
    def __init__(self, script): self.script = list(script); self.calls = []
    @property
    def chat(self): return SimpleNamespace(completions=SimpleNamespace(create=self._create))
    def _create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def make_agent(script, **kw):
    a = Agent.__new__(Agent)
    a.client, a.model, a.retriever = FakeClient(script), "gpt-4o-mini", BM25Retriever(CHUNKS)
    a.top_k, a.max_searches, a.max_steps = kw.get("top_k", 2), kw.get("max_searches", 2), 6
    a.budget, a.policy, a.temperature, a.citation_mode = 4000, "best_rank", 0, "id"
    return a


class AgentLoopTest(unittest.TestCase):
    def test_search_then_answer(self):
        a = make_agent([tool_call("search_law", {"query": "thử việc"}),
                        tool_call("answer", {"answer": "Không quá 60 ngày [a].", "citations": ["a"]})])
        out = a.run("Thử việc bao lâu?")
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["citations"], ["a"])
        self.assertEqual(out["n_searches"], 1)
        self.assertGreater(out["cost_usd"], 0)

    def test_citation_outside_context_is_repaired_then_abstains(self):
        a = make_agent([tool_call("search_law", {"query": "thử việc"}),
                        tool_call("answer", {"answer": "x [zzz]", "citations": ["zzz"]}),
                        tool_call("answer", {"answer": "x [zzz]", "citations": ["zzz"]})])
        out = a.run("Thử việc bao lâu?")
        self.assertEqual(out["status"], "abstain")
        self.assertEqual(out["stop_reason"], "invalid_citations")

    def test_alias_citations_map_back_to_chunk_ids(self):
        a = make_agent([tool_call("search_law", {"query": "thử việc"}),
                        tool_call("answer", {"answer": "Không quá 60 ngày [S1].", "citations": ["S1"]})])
        a.citation_mode = "alias"
        out = a.run("Thử việc bao lâu?")
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["citations"], ["a"])
        self.assertIn("[a]", out["answer"])

    def test_alias_unknown_label_rejected_with_valid_list(self):
        a = make_agent([tool_call("search_law", {"query": "thử việc"}),
                        tool_call("answer", {"answer": "x [S9]", "citations": ["S9"]}),
                        tool_call("abstain", {"reason": "r"})])
        a.citation_mode = "alias"
        out = a.run("Thử việc bao lâu?")
        self.assertEqual(out["status"], "abstain")
        repair = [m["content"] for m in a.client.calls[-1]["messages"] if m["role"] == "tool"][-1]
        self.assertIn("Nhãn hợp lệ: S1", repair)

    def test_search_limit_removes_search_tool(self):
        a = make_agent([tool_call("search_law", {"query": "a"}), tool_call("search_law", {"query": "b"}),
                        tool_call("abstain", {"reason": "không có"})], max_searches=2)
        out = a.run("Câu hỏi?")
        self.assertEqual(out["status"], "abstain")
        last_tools = [t["function"]["name"] for t in a.client.calls[-1]["tools"]]
        self.assertNotIn("search_law", last_tools)


if __name__ == "__main__":
    unittest.main()
