from core.intelligence.vision_vault import VisionVault


def test_vault_addition():
    vault = VisionVault(max_items=3)
    vault.add(b"fake_image_1")
    vault.add(b"fake_image_2")

    assert len(vault) == 2
    assert vault.has_context is True
    assert vault.get_context()[0].image_bytes == b"fake_image_1"


def test_vault_sliding_window():
    vault = VisionVault(max_items=2)
    vault.add(b"1")
    vault.add(b"2")
    vault.add(b"3")  # Should kick out "1"

    context = vault.get_context()
    assert len(context) == 2
    assert context[0].image_bytes == b"2"
    assert context[1].image_bytes == b"3"


def test_vault_clear():
    vault = VisionVault()
    vault.add(b"test")
    vault.clear()
    assert len(vault) == 0
    assert vault.has_context is False
