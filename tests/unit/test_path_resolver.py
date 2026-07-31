import os

import pytest

from aegis.resolution.path_resolver import ResolutionStatus, PathResolver


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Downloads" / "rapor.pdf").write_text("dummy")
    (tmp_path / "Arsiv2024").mkdir()
    (tmp_path / "Arsiv2025").mkdir()
    return str(tmp_path)


def test_yok_returns_not_needed(sandbox):
    resolver = PathResolver(sandbox)
    result = resolver.resolve("YOK")
    assert result.status == ResolutionStatus.NOT_NEEDED


def test_exact_match(sandbox):
    resolver = PathResolver(sandbox)
    result = resolver.resolve("rapor.pdf")
    assert result.status == ResolutionStatus.RESOLVED
    assert result.resolved_path == os.path.join(sandbox, "Downloads", "rapor.pdf")


def test_case_insensitive_match(sandbox):
    resolver = PathResolver(sandbox)
    result = resolver.resolve("RAPOR.PDF")
    assert result.status == ResolutionStatus.RESOLVED


def test_ambiguous_match(sandbox):
    resolver = PathResolver(sandbox)
    result = resolver.resolve("Arsiv")
    # "Arsiv" tam olarak hicbir klasorle eslesmiyor ama hem "Arsiv2024" hem
    # "Arsiv2025" icinde substring olarak geciyor -> belirsiz
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.matches) == 2


def test_not_found(sandbox):
    resolver = PathResolver(sandbox)
    result = resolver.resolve("olmayan_dosya.txt")
    assert result.status == ResolutionStatus.NOT_FOUND


def test_accent_normalized_match(tmp_path):
    (tmp_path / "Arşiv").mkdir()
    resolver = PathResolver(str(tmp_path))
    result = resolver.resolve("Arsiv")
    assert result.status == ResolutionStatus.RESOLVED
    assert result.resolved_path == str(tmp_path / "Arşiv")


def test_ambiguous_match_still_ambiguous_with_normalize_tier(sandbox):
    # Onceki davranis (substring kademesi) bu normalize kademesi eklendikten
    # sonra da bozulmamali: "Arsiv2024"/"Arsiv2025" normalize edildiginde
    # candidate ("Arsiv") ile TAM eslesmiyor (2024/2025 sonekleri yuzunden),
    # bu yuzden normalize kademesi 0 sonuc dondurur ve akis substring
    # kademesine duser - orada oldugu gibi belirsiz kalir.
    resolver = PathResolver(sandbox)
    result = resolver.resolve("Arsiv")
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.matches) == 2
