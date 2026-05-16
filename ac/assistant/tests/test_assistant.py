"""Personal Assistant — 测试"""
from __future__ import annotations
import sys, os, json, tempfile, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def clean_test_db():
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    os.unlink(f.name)
    return f.name


class TestAssistantSchemas:
    def test_tone_enum(self):
        from assistant.schemas import Tone
        assert Tone.FORMAL.value == "formal"
        assert Tone.CASUAL.value == "casual"

    def test_profile_defaults(self):
        from assistant.schemas import AssistantProfile
        p = AssistantProfile()
        assert p.identity.user_id == ""
        assert p.preferences.tone.value == "normal"
        assert p.safety.governance_required is True
        assert len(p.scheduling.slots) == 1

    def test_profile_merge(self):
        from assistant.schemas import AssistantProfile, Identity, Preferences, Tone
        base = AssistantProfile()
        base.identity.user_id = "user_a"
        overlay = AssistantProfile()
        overlay.identity = Identity(user_id="user_a", name="Alice")
        overlay.preferences.tone = Tone.CASUAL
        merged = base.merge(overlay)
        assert merged.identity.user_id == "user_a"
        assert merged.identity.name == "Alice"
        assert merged.preferences.tone == Tone.CASUAL


class TestProfileStore:
    def _cleanup(self, store, db):
        import sqlite3
        try:
            c = sqlite3.connect(db)
            c.close()
        except: pass
        try:
            os.unlink(db)
        except: pass

    def test_save_and_load(self):
        db = clean_test_db()
        from assistant.profile import ProfileStore
        from assistant.schemas import AssistantProfile, Identity, Tone
        store = ProfileStore(db)
        p = AssistantProfile()
        p.identity = Identity(user_id="u1", name="Test")
        p.preferences.tone = Tone.TECHNICAL
        store.save("u1", p)
        loaded = store.get("u1")
        assert loaded is not None
        assert loaded.identity.user_id == "u1"
        assert loaded.identity.name == "Test"
        assert loaded.preferences.tone == Tone.TECHNICAL
        self._cleanup(store, db)

    def test_delete(self):
        db = clean_test_db()
        from assistant.profile import ProfileStore
        from assistant.schemas import AssistantProfile
        store = ProfileStore(db)
        store.save("u1", AssistantProfile())
        store.delete("u1")
        assert store.get("u1") is None
        self._cleanup(store, db)


class TestRuleEngine:
    def test_rule_match_contains(self):
        from assistant.rules import RuleEngine, BehaviorRule, TriggerDef, TriggerMatch
        engine = RuleEngine()
        rule = BehaviorRule(
            rule_id="r1", name="greeting",
            triggers=[TriggerDef(match_type=TriggerMatch.CONTAINS, pattern="hello")],
        )
        assert engine._match_one("hello world", rule.triggers[0])
        assert not engine._match_one("goodbye", rule.triggers[0])

    def test_rule_match_regex(self):
        from assistant.rules import RuleEngine, BehaviorRule, TriggerDef, TriggerMatch
        engine = RuleEngine()
        rule = BehaviorRule(
            rule_id="r2",
            triggers=[TriggerDef(match_type=TriggerMatch.REGEX, pattern=r"\b\d{3,}\b")],
        )
        assert engine._match_one("code 12345", rule.triggers[0])
        assert not engine._match_one("no digits", rule.triggers[0])


class TestPersonalMemory:
    def test_remember_and_recall(self):
        db = clean_test_db()
        from assistant.memory import PersonalMemory
        mem = PersonalMemory(db)
        mem.remember("u1", "favorite_color", "blue")
        mem.remember("u1", "favorite_food", "pizza", confidence=0.9)
        results = mem.recall("u1", "color")
        assert len(results) >= 1
        assert results[0]["content"] == "blue"
        import sqlite3
        try:
            c = sqlite3.connect(db)
            c.close()
        except: pass
        try:
            os.unlink(db)
        except: pass


class TestCore:
    def test_assistant_create(self):
        db = clean_test_db()
        from assistant import create_assistant, AssistantOrchestrator
        pa = create_assistant("test_user", name="Tester", tone="formal", db_path=db)
        profile = pa.get_profile()
        assert profile.identity.user_id == "test_user"
        assert profile.identity.name == "Tester"
        try: os.unlink(db)
        except: pass

    def test_orchestrator_process(self):
        db = clean_test_db()
        from assistant import AssistantOrchestrator
        orb = AssistantOrchestrator(db_path=db)
        result = orb.process("测试查询", user_id="tester", session_id="sess_1")
        assert result["assistant"] is True
        assert result["user_id"] == "tester"
        assert result["session_id"] == "sess_1"
        assert "profile" in result
        try: os.unlink(db)
        except: pass

    def test_preferences_apply(self):
        db = clean_test_db()
        from assistant import create_assistant
        pa = create_assistant("p_user", tone="concise", db_path=db)
        dispatch_result = {"status": "matched", "matched": [{"name": "通用助手"}]}
        enriched = pa.apply_preferences(dispatch_result)
        assert enriched["_assistant"]["tone"] == "concise"
        assert enriched["_assistant"]["user_id"] == "p_user"
        try: os.unlink(db)
        except: pass


if __name__ == "__main__":
    import traceback
    tests = [
        TestAssistantSchemas, TestProfileStore,
        TestRuleEngine, TestPersonalMemory, TestCore,
    ]
    passed = 0
    failed = 0
    for cls in tests:
        inst = cls()
        for name in dir(cls):
            if name.startswith("test_"):
                try:
                    getattr(inst, name)()
                    print(f"  PASS  {cls.__name__}.{name}")
                    passed += 1
                except Exception as e:
                    print(f"  FAIL  {cls.__name__}.{name}: {e}")
                    traceback.print_exc()
                    failed += 1
    print(f"\n{'='*40}\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
