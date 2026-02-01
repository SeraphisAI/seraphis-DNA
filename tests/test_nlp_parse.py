from katopu_core.nlp import local_nl_to_edit

def test_prefix_deletion_tr():
    e = local_nl_to_edit("ilk 5 baz sil")
    assert e and e["op"]["type"] == "prefix_deletion"
    assert e["op"]["n"] == 5

def test_range_deletion():
    e = local_nl_to_edit("13..24 arasını sil")
    assert e and e["op"]["type"] == "deletion"
    assert e["op"]["i"] == 13 and e["op"]["j"] == 24

def test_insertion():
    e = local_nl_to_edit("18den sonra GCTAGC ekle")
    assert e and e["op"]["type"] == "insertion"
    assert e["op"]["i"] == 18
    assert e["op"]["seq"] == "GCTAGC"
