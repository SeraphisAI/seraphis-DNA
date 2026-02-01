from katopu_core.apply import local_apply

def test_apply_prefix_delete():
    res = local_apply("ATGC", "strict", {"schema":"katopu.editop.v2","op":{"type":"prefix_deletion","n":2}})
    assert res and res["after"] == "GC"
    assert res["metrics"]["delta_nt"] == -2
