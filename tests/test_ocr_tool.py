#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ocr_tool.py
@brief Tests of tools/ocr (OCR tool): keys and redaction, providers, pipeline, quota, RECITATION, suspects, cipher.

@details No network and no PDF are needed: providers are fakes, the renderer is replaced, the HTTP call of the
Gemini provider is overridden. The fake key is built at run time so that this file holds no key-like string.
"""

import io
import json
import logging
import os
import pathlib
import sys
import urllib.error

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.ocr import cipher, cli, config, keys, suspects, verify  # noqa: E402
from tools.ocr.ledger import Ledger, parse_queue  # noqa: E402
from tools.ocr.pipeline import ConfidentialError, Runner, combine  # noqa: E402
from tools.ocr.providers import REGISTRY, get_provider  # noqa: E402
from tools.ocr.providers.base import Provider, ProviderError, Result  # noqa: E402
from tools.ocr.providers.gemini import GeminiProvider  # noqa: E402
from tools.ocr.providers.local import LocalProvider  # noqa: E402

FAKE_KEY = "AIza" + "Sy" + "x" * 33          # 39 characters, built here so the source has no key-like text


class FakeProvider(Provider):
    """!
    @brief Scripted provider: answers are popped from a list; an Exception in the list is raised.
    """

    name = "fake"
    online = True
    default_model = "fake-1"

    def __init__(self, answers):
        """!
        @brief Create the fake.
        @param answers List of Result or Exception, one per call.
        @return None
        """
        self.answers, self.calls = list(answers), []

    def transcribe(self, image_bytes, prompt, options):
        """!
        @brief Pop the next scripted answer.
        @param image_bytes Image bytes (recorded).
        @param prompt      Prompt (unused).
        @param options     Options (the model is recorded).
        @return Result The scripted result.
        """
        self.calls.append((image_bytes, options.get("model")))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def runner(tmp_path, provider, **kw):
    """!
    @brief A runner with fake rendering and no waiting.
    @param tmp_path Output folder.
    @param provider Provider.
    @param kw       Extra Runner arguments.
    @return Runner The runner.
    """
    return Runner(provider, tmp_path, Ledger(tmp_path / "usage.json"), pause=0, sleep=lambda s: None,
                  renderer=lambda pdf, page, dpi, clip: f"png{page}{clip}".encode(),
                  info=lambda pdf: ("", ""), **kw)


# ---------------------------------------------------------------- keys
def test_key_from_environment_first(monkeypatch, tmp_path):
    f = tmp_path / ".ocr_keys"
    f.write_text("gemini=fromfile12345678\n")
    f.chmod(0o600)
    monkeypatch.setenv("GEMINI_API_KEY", "fromenv12345678")
    assert keys.load_key("gemini", ("GEMINI_API_KEY",), [tmp_path]) == "fromenv12345678"


def test_key_from_file_and_comment_lines(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    f = tmp_path / ".ocr_keys"
    f.write_text("# a comment\nother=zzzzzzzzzzzz\ngemini = 'fromfile12345678'\n")
    f.chmod(0o600)
    assert keys.load_key("gemini", ("GEMINI_API_KEY",), [tmp_path]) == "fromfile12345678"


def test_world_readable_key_file_is_refused_without_showing_the_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    f = tmp_path / ".ocr_keys"
    f.write_text("gemini=fromfile12345678\n")
    f.chmod(0o644)
    with pytest.raises(keys.KeyError_) as e:
        keys.load_key("gemini", ("GEMINI_API_KEY",), [tmp_path])
    assert "chmod 600" in str(e.value) and "fromfile12345678" not in str(e.value)


def test_missing_key_message_names_the_variable_and_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(keys.KeyError_) as e:
        keys.load_key("gemini", ("GEMINI_API_KEY",), [tmp_path])
    assert "GEMINI_API_KEY" in str(e.value) and ".ocr_keys" in str(e.value)


def test_redact_removes_registered_and_key_like_strings():
    keys.register_secret("registered-secret-value")
    t = keys.redact(f"bad registered-secret-value and {FAKE_KEY} and api_key=abcdefghijklmnop1234 and AQ." + "b" * 40)
    assert "registered-secret-value" not in t and FAKE_KEY not in t and "abcdefghijklmnop1234" not in t
    assert "AQ." + "b" * 40 not in t and "[KEY]" in t


def test_main_checkout_is_searched_from_a_worktree():
    roots = keys.project_roots()
    assert roots[0] == keys.REPO_ROOT and all(r.is_dir() for r in roots)


# ---------------------------------------------------------------- small helpers
def test_parse_pages():
    assert config.parse_pages("3,5-6") == [3, 5, 6]
    assert config.parse_pages("all", 4) == [1, 2, 3, 4]
    assert config.parse_pages("7-", 9) == [7, 8, 9]
    with pytest.raises(ValueError):
        config.parse_pages("x")


def test_parse_queue_table_and_plain_lines():
    items = parse_queue("| # | file | page | why |\n| -: | :-- | -: | :-- |\n| 1 | Lemczyk1992.pdf | 6 | scan |\nShen.pdf:3\nOther 4\n")
    assert [(i.file, i.page) for i in items] == [("Lemczyk1992", 6), ("Shen", 3), ("Other", 4)]


def test_confidential_names():
    assert config.is_confidential(pathlib.Path("OdbppSpec81U4.pdf"))
    assert config.is_confidential(pathlib.Path("x.pdf"), "Siemens CONFIDENTIAL draft")
    assert config.is_confidential(pathlib.Path("Muzychka2003.pdf")) is None


def test_registry_and_local_command():
    assert {"gemini", "local"} <= set(REGISTRY)
    assert get_provider("local").online is False and get_provider("gemini").online is True
    cmd = LocalProvider(folder="/x", python="/py").command(pathlib.Path("a.pdf"), pathlib.Path("o.md"), "ovis")
    assert cmd[:2] == ["/py", "/x/pdf2md_local.py"] and "--page-markers" in cmd and "ovis" in cmd


# ---------------------------------------------------------------- Gemini provider (no network)
class FakeGemini(GeminiProvider):
    """!
    @brief Gemini provider whose HTTP call is scripted.
    """

    def __init__(self, answers):
        """!
        @brief Create it.
        @param answers List of dict responses or exceptions.
        @return None
        """
        super().__init__(key=FAKE_KEY, retries=3, first_pause=0.0, sleep=lambda s: None)
        self.answers, self.urls = list(answers), []

    def _post(self, url, body, timeout):
        """!
        @brief Scripted POST.
        @param url     URL (recorded).
        @param body    Body (unused).
        @param timeout Unused.
        @return dict The next response.
        """
        self.urls.append(url)
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def http_error(code, body):
    """!
    @brief Build an HTTPError with a body.
    @param code HTTP status.
    @param body Body text.
    @return urllib.error.HTTPError The error.
    """
    return urllib.error.HTTPError("http://x", code, "err", {}, io.BytesIO(body.encode()))


OK_RESPONSE = {"candidates": [{"content": {"parts": [{"text": "hello $x$"}]}, "finishReason": "STOP"}]}


def test_gemini_retries_on_500_then_succeeds_and_key_not_in_url():
    g = FakeGemini([http_error(500, "boom"), http_error(429, "rate limit per minute"), OK_RESPONSE])
    r = g.transcribe(b"png", "p", {})
    assert r.text == "hello $x$" and not r.recitation and len(g.urls) == 3
    assert all(FAKE_KEY not in u and "key=" not in u for u in g.urls)


def test_gemini_daily_quota_stops_at_once():
    g = FakeGemini([http_error(429, '{"error":{"message":"Quota exceeded for ... PerDay ..."}}')])
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {})
    assert e.value.quota_exhausted and len(g.urls) == 1


def test_gemini_gives_up_after_the_retries():
    g = FakeGemini([http_error(503, "busy")] * 3)
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {})
    assert e.value.status == 503 and not e.value.quota_exhausted


def test_gemini_recitation_is_a_result_not_an_error():
    g = FakeGemini([{"candidates": [{"finishReason": "RECITATION"}]}])
    r = g.transcribe(b"png", "p", {})
    assert r.recitation and r.text == ""


def test_gemini_error_text_never_holds_the_key():
    g = FakeGemini([http_error(400, f"bad key {FAKE_KEY} in request")])
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {})
    assert FAKE_KEY not in str(e.value)


# ---------------------------------------------------------------- pipeline
PDF = pathlib.Path("Paper.pdf")


def test_page_written_with_marker_ledger_and_resume(tmp_path):
    p = FakeProvider([Result("text one")])
    r = runner(tmp_path, p)
    o = r.run_page(PDF, 3)
    assert o.status == "ok" and (tmp_path / "Paper_p3.md").read_text() == "<!-- page 3 -->\ntext one"
    e = json.loads((tmp_path / "usage.json").read_text())[0]
    assert e["file"] == "Paper" and e["page"] == 3 and e["ok"] and e["requests"] == 1 and e["provider"] == "fake"
    assert r.run_page(PDF, 3).status == "skipped" and len(p.calls) == 1       # resume: no new request


def test_recitation_retries_with_half_page_crops(tmp_path):
    p = FakeProvider([Result("", "RECITATION", recitation=True), Result("top"), Result("bottom")])
    o = runner(tmp_path, p).run_page(PDF, 2)
    assert o.status == "ok" and "top" in o.text and "bottom" in o.text and "half-page crops" in o.text
    clips = [c[0].decode() for c in p.calls]
    assert "None" in clips[0] and "0.55" in clips[1] and "0.45" in clips[2]
    assert json.loads((tmp_path / "usage.json").read_text())[0]["requests"] == 3


def test_recitation_everywhere_ends_as_failed_with_a_note(tmp_path):
    rec = Result("", "RECITATION", recitation=True)
    p = FakeProvider([rec, rec, Result("x"), rec, rec, rec])      # full, top, bottom(ok), then fallbacks refuse
    o = runner(tmp_path, p).run_page(PDF, 2)
    assert o.status == "failed" and "RECITATION" in o.note and not (tmp_path / "Paper_p2.md").exists()


def test_fallback_model_after_refused_crops(tmp_path):
    rec = Result("", "RECITATION", recitation=True)
    p = FakeProvider([rec, rec, rec, Result("from fallback")])
    p.name = "gemini"                                              # take the fallbacks of data/models.json
    o = runner(tmp_path, p).run_page(PDF, 2)
    assert o.status == "ok" and o.text == "from fallback" and p.calls[-1][1] == config.models()["gemini"]["fallbacks"][0]


def test_quota_stops_the_run_and_records_the_page(tmp_path):
    p = FakeProvider([Result("one"), ProviderError("HTTP 429: PerDay", status=429, quota_exhausted=True), Result("never")])
    r = runner(tmp_path, p)
    outs = r.run_pages(PDF, [1, 2, 3])
    assert [o.status for o in outs] == ["ok", "quota"] and len(p.calls) == 2
    last = json.loads((tmp_path / "usage.json").read_text())[-1]
    assert last["page"] == 2 and last["ok"] is False and "quota" in last["note"]
    assert Ledger(tmp_path / "usage.json").done() == {("Paper", 1)}


def test_daily_limit_counts_requests_from_the_ledger(tmp_path):
    p = FakeProvider([Result("a"), Result("b")])
    r = runner(tmp_path, p, daily_limit=1)
    assert [o.status for o in r.run_pages(PDF, [1, 2])] == ["ok", "limit"]


def test_three_failures_in_a_row_stop_the_run(tmp_path):
    p = FakeProvider([ProviderError("HTTP 400")] * 3 + [Result("late")])
    outs = runner(tmp_path, p).run_pages(PDF, [1, 2, 3, 4])
    assert [o.status for o in outs] == ["failed"] * 3


def test_confidential_file_is_refused_by_name_unless_allowed(tmp_path):
    spec = pathlib.Path("OdbppSpec81U4.pdf")
    p = FakeProvider([Result("x")])
    with pytest.raises(ConfidentialError):
        runner(tmp_path, p).run_page(spec, 1)
    assert p.calls == []
    assert runner(tmp_path, p, allow_confidential=True).run_page(spec, 1).status == "ok"


def test_confidential_text_in_the_pdf_is_refused(tmp_path):
    r = runner(tmp_path, FakeProvider([Result("x")]))
    r._info = lambda pdf: ("Siemens Confidential", "")
    with pytest.raises(ConfidentialError):
        r.run_page(pathlib.Path("Paper.pdf"), 1)


def test_local_provider_is_not_subject_to_the_confidential_guard(tmp_path):
    p = FakeProvider([Result("x")])
    p.online = False
    assert runner(tmp_path, p).run_page(pathlib.Path("OdbppSpec81U4.pdf"), 1).status == "ok"


def test_combine_numbers_pages(tmp_path):
    outs = runner(tmp_path, FakeProvider([Result("a"), Result("b")])).run_pages(PDF, [4, 5])
    assert combine(outs) == "<!-- page 4 -->\na\n\n<!-- page 5 -->\nb"


# ---------------------------------------------------------------- the key never escapes
class LeakyProvider(FakeProvider):
    """!
    @brief Provider whose exception text contains the key (a bad server echo or a careless message).
    """

    def transcribe(self, image_bytes, prompt, options):
        """!
        @brief Always raise with the key inside.
        @param image_bytes Unused.
        @param prompt      Unused.
        @param options     Unused.
        @return Result Never returns.
        """
        raise RuntimeError(f"connection failed for https://x/?key={FAKE_KEY} using {FAKE_KEY}")


def test_exception_with_the_key_never_reaches_stdout_stderr_logs_or_ledger(tmp_path, capfd, caplog, monkeypatch):
    keys.register_secret(FAKE_KEY)
    caplog.set_level(logging.DEBUG)
    r = runner(tmp_path, LeakyProvider([]))
    o = r.run_page(PDF, 1)
    assert o.status == "failed" and FAKE_KEY not in o.note
    assert FAKE_KEY not in (tmp_path / "usage.json").read_text()
    # The command line: a leaky provider through main() with the redacting log filter and the last-resort handler.
    monkeypatch.setitem(REGISTRY, "gemini", lambda: LeakyProvider([]))
    monkeypatch.setattr(cli, "resolve_pdf", lambda arg, papers: PDF)
    monkeypatch.setattr(cli.render, "page_count", lambda pdf: 3)
    monkeypatch.setattr("tools.ocr.pipeline.render.render_page", lambda *a, **k: b"png")
    monkeypatch.setattr("tools.ocr.pipeline.render.first_page_info", lambda pdf: ("", ""))
    code = cli.main(["--papers", str(tmp_path), "transcribe", "Paper", "--pages", "1", "--pause", "0"])
    out = capfd.readouterr()
    assert code == 1
    assert FAKE_KEY not in out.out and FAKE_KEY not in out.err
    assert all(FAKE_KEY not in rec.getMessage() for rec in caplog.records)


def test_last_resort_handler_redacts_a_raw_exception(capfd, monkeypatch):
    keys.register_secret(FAKE_KEY)
    monkeypatch.setitem(cli.COMMANDS, "providers", lambda a, p: (_ for _ in ()).throw(RuntimeError("boom " + FAKE_KEY)))
    assert cli.main(["providers"]) == 1
    out = capfd.readouterr()
    assert FAKE_KEY not in out.out + out.err and "[KEY]" in out.err


# ---------------------------------------------------------------- cipher
def test_cipher_decodes_the_base36_pairs():
    assert cipher.decode_token("D4D6CTD7") == "pres"
    assert cipher.decode_token("BTBUCBCCCABTBVCC") == "ABSTRACT"
    assert cipher.decode_token("ADD9DC") == "flux"                   # ligature code 13
    assert cipher.decode_text("see CP D7CXD1D4D0CT CVCTD3D1CTD8D6CXCR") == ("see a simple geometric", 3)


def test_cipher_leaves_ordinary_words_and_numbers_alone():
    for word in ("RESOLUTION", "METHOD", "2024", "A1B2", "HELZEL"):
        assert cipher.decode_token(word) is None
    assert cipher.decode_text("EMBEDDED GEOMETRIES 2024")[1] == 0


# ---------------------------------------------------------------- suspects
def test_suspect_reasons():
    assert suspects.analyse_page("a b c", None, 200) == ["low_words"]
    assert "undecoded_equations" in suspects.analyse_page("word " * 300 + "<!-- formula-not-decoded -->", None, 300)
    assert "cipher" in suspects.analyse_page("D4D6CTD7 CTD2D8D7 CXD1D4D0CT CVCTD3D1CTD8D6CXCR D8CWCTD6D1CPD0 " * 3, None, 15)
    assert "broken_font" in suspects.analyse_page(" ".join(["Q1X9ZZ7K"] * 30), None, 30)
    assert suspects.analyse_page("normal text " * 100, "A normal readable paragraph of text. " * 10, 200) == []


def test_garbage_text_layer_detector():
    assert suspects.garbage_text_layer("\x07\x06\x0b\x05\t\x02\x19\n" * 20)
    assert suspects.garbage_text_layer("xkqz wrtp bcdf ghjk plmn qrst vwxz " * 10)
    assert not suspects.garbage_text_layer("This is an ordinary English sentence about thermal spreading resistance. " * 5)


def test_printed_page_number_and_offset():
    assert suspects.printed_page_number("Journal of Heat Transfer\n413\nBody text here\nmore") == 413
    assert suspects.printed_page_number("Header\nBody\nPage 7") == 7
    assert suspects.printed_page_number("no numbers at all\nhere") is None
    assert suspects.page_offset({1: 413, 2: 414, 3: 415}) == -412
    assert suspects.page_offset({1: 10}) is None


def test_suspect_report_lists_both_page_numbers(tmp_path):
    res = {"Paper": {"pages": 5, "offset": -412, "median_words": 300,
                     "suspect": [{"pdf_page": 2, "printed_page": 414, "reasons": ["cipher"]}]}}
    suspects.write_reports(res, tmp_path / "s.json", tmp_path / "s.md")
    assert "2 / 414: cipher" in (tmp_path / "s.md").read_text()
    assert json.loads((tmp_path / "s.json").read_text())["Paper"]["offset"] == -412


# ---------------------------------------------------------------- verify
def test_verify_page_embeds_image_and_escapes_text(tmp_path):
    out = verify.write_verify(b"\x89PNGdata", "a < b & $x$", "Paper.pdf - PDF page 2 (printed page 414)", tmp_path / "v" / "p.html")
    h = out.read_text()
    assert "data:image/png;base64," in h and "a &lt; b &amp; $x$" in h and "printed page 414" in h
