from ac.dual_inference import get_dual
from ac.schema_contract import DualInferenceResult


def test_dual_inference_returns_valid_contract():
    dual = get_dual()
    result = dual.infer("1+1=?")
    validated = DualInferenceResult(**result)
    assert validated.consistent in (True, False)
    print("[PASS] 心脏起搏成功：推理+契约验证通过")


if __name__ == "__main__":
    test_dual_inference_returns_valid_contract()
