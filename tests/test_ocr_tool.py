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
from tools.ocr.providers.anthropic import AnthropicProvider  # noqa: E402
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
    assert cipher.decode_text("see CP D7CXD1D4D0CT CVCTD3D1CTD8D6CXCR", force=True) == ("see a simple geometric", 3)


CIPHER_PAGE = ("BYD3D6 CP CRD3D1D4D3D9D2CS D7DDD7D8CTD1 BXD5BA B4BKB5 CXD7 DBD6CXD8D8CTD2 D8D3 D6CTD4D6CTB9 D7CTD2D8 "
               "D8CWCT D8D3D8CPD0 D8CWCTD6D1CPD0 D6CTD7CXD7D8CPD2CRCT")     # opening of Muzychka2003Part1 p3


def test_cipher_decodes_a_ciphered_page_with_its_equation_number():
    text, n = cipher.decode_text("<!-- page 3 -->\n" + CIPHER_PAGE)
    assert text.startswith("<!-- page 3 -->\nFor a compound system Eq. (8) is written") and n == 15
    assert "the total thermal resistance" in text


def test_cipher_leaves_acronyms_of_ordinary_pages_alone():
    # AC would read "fi", DC "x" and ACDC "fix" if every token were decoded (24 such tokens in a TI note).
    plain = "<!-- page 1 -->\nThe AC and DC supplies of the ACDC stage. " * 5 + "\n<!-- page 2 -->\n" + CIPHER_PAGE
    text, n = cipher.decode_text(plain)
    assert text.count("The AC and DC supplies of the ACDC stage.") == 5 and "Eq. (8)" in text and n == 15


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


# ---------------------------------------------------------------- review: Gemini errors as the API sends them
DAILY_429 = json.dumps({"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": ("You exceeded your current quota, please check your plan and billing details. For more information on "
                "this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, "
                "head to: https://ai.dev/usage?tab=rate-limit.\n* Quota exceeded for metric: "
                "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: "
                "gemini-3.1-flash-lite\nPlease retry in 41.47s."),
    "details": [
        {"@type": "type.googleapis.com/google.rpc.Help",
         "links": [{"description": "Learn more about Gemini API quotas", "url": "https://ai.google.dev/gemini-api/docs/rate-limits"}]},
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                         "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                         "quotaDimensions": {"location": "global", "model": "gemini-3.1-flash-lite"}, "quotaValue": "20"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "41s"}]}}, indent=2)


def test_daily_quota_is_found_in_the_details_of_a_long_body():
    # The quota id sits after about 900 characters: a body cut at 600 characters made it a per-minute retry.
    assert DAILY_429.index("PerDay") > 600
    g = FakeGemini([http_error(429, DAILY_429)])
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {})
    assert e.value.quota_exhausted and not e.value.retryable and len(g.urls) == 1
    assert "PerDay" in str(e.value) and "Quota exceeded" in str(e.value)


def test_per_minute_429_waits_the_delay_the_server_asks_and_logs_each_retry(caplog):
    body = DAILY_429.replace("PerDay", "PerMinute")
    waits = []
    g = FakeGemini([http_error(429, body), OK_RESPONSE])
    g._sleep = waits.append
    caplog.set_level(logging.WARNING, logger="tools.ocr")
    r = g.transcribe(b"png", "p", {})
    assert r.text == "hello $x$" and waits == [41.0] and r.extra["attempts"] == 2
    assert any("attempt 1 of 3" in rec.getMessage() for rec in caplog.records)


def test_prompt_blocked_and_cut_answers_are_reported(tmp_path):
    g = FakeGemini([{"promptFeedback": {"blockReason": "OTHER"}}])
    assert g.transcribe(b"png", "p", {}).finish_reason == "NO_CANDIDATE:OTHER"
    o = runner(tmp_path, FakeProvider([Result("half a page", "MAX_TOKENS")])).run_page(PDF, 1)
    assert o.status == "ok" and "may be incomplete" in o.note


def test_ledger_counts_the_http_retries_as_requests(tmp_path):
    g = FakeGemini([http_error(503, "busy"), OK_RESPONSE])
    runner(tmp_path, g).run_page(PDF, 1)
    assert json.loads((tmp_path / "usage.json").read_text())[0]["requests"] == 2


def test_check_key_makes_one_attempt_and_never_sleeps(monkeypatch, capfd):
    # The slow check-key: a 503 or 429 used to wait 20 + 40 + 80 s in silence before FAIL.
    slept = []
    g = FakeGemini([http_error(503, "busy")] * 4)
    g._sleep = slept.append
    monkeypatch.setitem(REGISTRY, "gemini", lambda: g)
    monkeypatch.setattr(cli.render, "synthetic_png", lambda: b"png")
    assert cli.main(["--papers", "/nonexistent", "check-key"]) == 1
    out = capfd.readouterr().out
    assert out.startswith("FAIL") and "HTTP 503" in out and len(g.urls) == 1 and slept == []


# ---------------------------------------------------------------- review: the confidential guard
def _confidential_data(tmp_path, monkeypatch, sha=()):
    """!
    @brief Point the tool at a private confidential.json.
    @param tmp_path  Folder for the file.
    @param monkeypatch The pytest monkeypatch fixture.
    @param sha       SHA-256 values to list.
    @return None
    """
    data = tmp_path / "data"
    data.mkdir()
    for name in ("models.json", "prompt.txt"):
        (data / name).write_bytes((config.DATA / name).read_bytes())
    cfg = json.loads((config.DATA / "confidential.json").read_text())
    cfg["sha256"] = list(sha)
    (data / "confidential.json").write_text(json.dumps(cfg))
    monkeypatch.setattr(config, "DATA", data)


def test_a_renamed_confidential_file_is_refused_by_its_hash(tmp_path, monkeypatch):
    f = tmp_path / "spec.pdf"
    f.write_bytes(b"%PDF-1.4 bytes of a confidential file")
    _confidential_data(tmp_path, monkeypatch, [config.file_sha256(f)])
    assert "SHA-256" in config.is_confidential(f)
    p = FakeProvider([Result("x")])
    with pytest.raises(ConfidentialError):
        runner(tmp_path, p).run_page(f, 1)
    assert p.calls == []


def test_the_shipped_list_holds_the_odbpp_hash_and_matches_its_title():
    assert len(json.loads((config.DATA / "confidential.json").read_text())["sha256"]) >= 1
    assert config.is_confidential(pathlib.Path("renamed.pdf"), "", "ODB++Design Format Specification Siemens")
    assert config.is_confidential(pathlib.Path("RENAMED-CONFIDENTIAL-copy.pdf"))


def test_an_unreadable_pdf_is_not_sent(tmp_path):
    r = runner(tmp_path, FakeProvider([Result("x")]))
    r._info = lambda pdf: (_ for _ in ()).throw(RuntimeError("broken xref"))
    with pytest.raises(ConfidentialError):
        r.run_page(PDF, 1)


def test_check_key_with_a_confidential_pdf_is_refused_before_any_request(tmp_path, monkeypatch, capfd):
    (tmp_path / "pdf").mkdir()
    spec = tmp_path / "pdf" / "OdbppSpec81U4.pdf"
    spec.write_bytes(b"%PDF")
    g = FakeGemini([OK_RESPONSE])
    monkeypatch.setitem(REGISTRY, "gemini", lambda: g)
    monkeypatch.setattr("tools.ocr.pipeline.render.first_page_info", lambda pdf: ("", ""))
    assert cli.main(["--papers", str(tmp_path), "check-key", "--pdf", "OdbppSpec81U4"]) == 3
    assert g.urls == [] and "confidential" in capfd.readouterr().err


# ---------------------------------------------------------------- review: a second provider through the command line
class EchoProvider(Provider):
    """!
    @brief A trivial second provider (offline) that answers with the size of the image.
    """

    name = "echo"
    online = False
    default_model = "echo-1"

    def transcribe(self, image_bytes, prompt, options):
        """!
        @brief Answer with the image size.
        @param image_bytes Image bytes.
        @param prompt      Unused.
        @param options     Options.
        @return Result The answer.
        """
        return Result(f"{len(image_bytes)} bytes", model=options.get("model", ""))


def test_a_second_provider_runs_through_the_command_line(tmp_path, monkeypatch, capfd):
    monkeypatch.setitem(REGISTRY, "echo", EchoProvider)
    monkeypatch.setattr(cli, "resolve_pdf", lambda arg, papers: PDF)
    monkeypatch.setattr(cli.render, "page_count", lambda pdf: 2)
    monkeypatch.setattr("tools.ocr.pipeline.render.render_page", lambda *a, **k: b"12345")
    assert cli.main(["--papers", str(tmp_path), "transcribe", "Paper", "--pages", "all", "--provider", "echo",
                     "--pause", "0"]) == 0
    assert (tmp_path / "ocr" / "echo" / "Paper_p2.md").read_text() == "<!-- page 2 -->\n5 bytes"
    led = json.loads((tmp_path / "ocr" / "usage.json").read_text())
    assert [e["provider"] for e in led] == ["echo", "echo"] and led[0]["model"] == "echo-1"
    monkeypatch.setattr(cli.render, "synthetic_png", lambda: b"png")
    assert cli.main(["--papers", str(tmp_path), "check-key", "--provider", "echo"]) == 0   # no models.json entry
    assert "OK (echo-1" in capfd.readouterr().out


def test_local_converter_gets_no_api_key_in_its_environment(monkeypatch):
    from tools.ocr.providers.local import scrubbed_environment
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    env = scrubbed_environment()
    assert "GEMINI_API_KEY" not in env and "GOOGLE_API_KEY" not in env and "PATH" in env


# ---------------------------------------------------------------- review: pages, verify and rendering
def test_printed_page_follows_the_offset_and_journal_footers():
    assert suspects.printed_page(323, 309, 14) == 309
    assert suspects.printed_page(10, 314, 14) is None            # a contents line before printed page 1
    assert suspects.printed_page(132, 0, 14) == 118               # a table entry "0" is not the page number
    assert suspects.printed_page(5, 7, None) == 7
    assert suspects.printed_page_number("Body\ntext\nJournal of Electronic Packaging\nJUNE 2003, Vol. 125 \u00d5 179") == 179
    assert suspects.printed_page_number("Body\ntext\n180 \u00d5 Vol. 125, JUNE 2003\nTransactions of the ASME") == 180


def test_verify_page_forbids_scripts_and_remote_content(tmp_path):
    hostile = "<script>alert(1)</script><img src=x onerror=alert(2)> </pre><iframe src='http://evil'>"
    h = verify.build_html(b"png", hostile, "t</title><script>x</script>")
    assert "<script>" not in h and "<iframe" not in h and "<img src=x" not in h
    assert "default-src 'none'" in h and "img-src data:" in h


def test_an_oversized_page_is_rendered_at_a_lower_resolution(tmp_path):
    pdfium = pytest.importorskip("pypdfium2")
    pil = pytest.importorskip("PIL.Image")
    import io
    from tools.ocr import render
    doc = pdfium.PdfDocument.new()
    doc.new_page(14400, 14400)                                    # 200 x 200 inch: 1.6e9 pixels at 200 dpi
    doc.save(str(tmp_path / "big.pdf"))
    png = render.render_page(tmp_path / "big.pdf", 1)
    width, height = pil.open(io.BytesIO(png)).size
    assert width * height <= render.MAX_PIXELS


def test_ocr_folder_is_ocr_and_an_old_gemini_folder_is_still_found(tmp_path):
    assert cli.ocr_dir(tmp_path) == tmp_path / "ocr"
    assert cli.out_dir(tmp_path, "gemini") == tmp_path / "ocr"
    assert cli.out_dir(tmp_path, "local") == tmp_path / "ocr" / "local"
    (tmp_path / "gemini").mkdir()                       # a library made before the rename
    assert cli.ocr_dir(tmp_path) == tmp_path / "gemini"
    (tmp_path / "ocr").mkdir()                          # once ocr/ exists it wins
    assert cli.ocr_dir(tmp_path) == tmp_path / "ocr"


# ---------------------------------------------------------------- Anthropic provider (no network)
ANT_KEY = "sk-ant-" + "usr-" + "Ab1_-" * 8          # built here so the source has no key-like text


class FakeAnthropic(AnthropicProvider):
    """!
    @brief Anthropic provider whose HTTP call is scripted.
    """

    def __init__(self, answers):
        """!
        @brief Create it.
        @param answers List of dict responses or exceptions.
        @return None
        """
        super().__init__(key=ANT_KEY, retries=3, first_pause=0.0, sleep=lambda s: None)
        self.answers, self.urls, self.bodies, self.sleeps = list(answers), [], [], []
        self._sleep = self.sleeps.append

    def _post(self, url, body, timeout):
        """!
        @brief Scripted POST.
        @param url     URL (recorded).
        @param body    Body (recorded).
        @param timeout Unused.
        @return dict The next response.
        """
        self.urls.append(url)
        self.bodies.append(json.loads(body))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def ant_error(code, kind, message, headers=None):
    """!
    @brief Build an HTTPError in the shape of the Messages API.
    @param code    HTTP status.
    @param kind    Error type.
    @param message Error message.
    @param headers Response headers.
    @return urllib.error.HTTPError The error.
    """
    body = json.dumps({"type": "error", "error": {"type": kind, "message": message}})
    return urllib.error.HTTPError("http://x", code, "err", headers or {}, io.BytesIO(body.encode()))


ANT_OK = {"content": [{"type": "text", "text": "page $x^2$"}], "stop_reason": "end_turn",
          "usage": {"input_tokens": 1500, "output_tokens": 300}}


def test_anthropic_request_shape_usage_and_key_not_in_url():
    g = FakeAnthropic([ANT_OK])
    r = g.transcribe(b"png", "prompt", {"model": "claude-haiku-5-5"})
    assert r.text == "page $x^2$" and r.extra["usage"] == {"input_tokens": 1500, "output_tokens": 300}
    b = g.bodies[0]
    assert b["model"] == "claude-haiku-5-5" and b["max_tokens"] >= 4096
    assert b["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    assert ANT_KEY not in g.urls[0] and "key" not in g.urls[0]
    assert "temperature" not in b      # the current models answer HTTP 400 to it


def test_anthropic_429_waits_for_retry_after_and_overloaded_529_retries():
    g = FakeAnthropic([ant_error(429, "rate_limit_error", "slow down", {"retry-after": "7"}),
                       ant_error(529, "overloaded_error", "Overloaded"), ANT_OK])
    assert g.transcribe(b"png", "p", {}).text and g.sleeps[0] == 7.0 and len(g.urls) == 3


def test_anthropic_credit_and_usage_limit_errors_stop_at_once():
    for code, msg in ((400, "Your credit balance is too low to access the Anthropic API."),
                      (429, "You have reached your specified API usage limits.")):
        g = FakeAnthropic([ant_error(code, "invalid_request_error", msg)])
        with pytest.raises(ProviderError) as e:
            g.transcribe(b"png", "p", {})
        assert e.value.quota_exhausted and not e.value.retryable and len(g.urls) == 1


def test_anthropic_permission_error_is_not_retried():
    g = FakeAnthropic([ant_error(403, "permission_error", "not allowed")])
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {})
    assert e.value.status == 403 and not e.value.retryable and not e.value.quota_exhausted and len(g.urls) == 1


def test_anthropic_max_tokens_is_a_split_and_refusal_a_recitation():
    g = FakeAnthropic([{"content": [{"type": "text", "text": "cut"}], "stop_reason": "max_tokens", "usage": {}},
                       {"content": [], "stop_reason": "refusal", "usage": {}}])
    assert g.transcribe(b"png", "p", {}).split
    assert g.transcribe(b"png", "p", {}).recitation


def test_anthropic_error_with_a_usr_key_never_reaches_any_output(tmp_path, capfd, caplog):
    keys.register_secret(ANT_KEY)
    # An unregistered key of the same family is removed by the pattern alone.
    other = "sk-ant-" + "usr-" + "Zz9-_" * 8
    assert other not in keys.redact(f"bad {other}") and ANT_KEY not in keys.redact(f"x-api-key: {ANT_KEY}")
    caplog.set_level(logging.DEBUG)
    g = FakeAnthropic([ant_error(401, "authentication_error", f"invalid x-api-key {ANT_KEY} / {other}")])
    r = runner(tmp_path, g)
    o = r.run_page(PDF, 1)
    assert o.status == "failed"
    out = capfd.readouterr()
    blob = o.note + (tmp_path / "usage.json").read_text() + out.out + out.err + caplog.text
    assert ANT_KEY not in blob and other not in blob


def test_anthropic_tokens_reach_the_ledger_and_max_tokens_is_asked_in_halves(tmp_path):
    cut = {"content": [{"type": "text", "text": "cut"}], "stop_reason": "max_tokens",
           "usage": {"input_tokens": 100, "output_tokens": 8192}}
    half = {"content": [{"type": "text", "text": "half"}], "stop_reason": "end_turn",
            "usage": {"input_tokens": 50, "output_tokens": 20}}
    r = runner(tmp_path, FakeAnthropic([cut, half, half]))
    o = r.run_page(PDF, 1)
    assert o.status == "ok" and "half-page crops" in o.text
    e = json.loads((tmp_path / "usage.json").read_text())[0]
    assert e["provider"] == "anthropic" and e["input_tokens"] == 200 and e["output_tokens"] == 8232
    assert Ledger(tmp_path / "usage.json").tokens_today("anthropic")["output_tokens"] == 8232


def test_anthropic_is_registered_with_its_key_variable_and_models():
    assert REGISTRY["anthropic"].key_env == ("ANTHROPIC_API_KEY",)
    assert config.models()["anthropic"]["default"] == "claude-sonnet-5-5"


def test_anthropic_prose_refusal_and_content_filter_take_the_recitation_path(tmp_path):
    # "I can't transcribe ... here is a summary" (end_turn) and HTTP 400 "content filtering policy" are refusals of the page.
    prose = {"content": [{"type": "text", "text": "I can't transcribe this page in full, because it is text from a published article. Here is a summary of the page."}], "stop_reason": "end_turn", "usage": {}}
    half = {"content": [{"type": "text", "text": "half $x$"}], "stop_reason": "end_turn", "usage": {}}
    assert FakeAnthropic([prose]).transcribe(b"png", "p", {}).recitation
    assert not FakeAnthropic([ANT_OK]).transcribe(b"png", "p", {}).recitation
    def blocked():
        return ant_error(400, "invalid_request_error", "Output blocked by content filtering policy")
    r = FakeAnthropic([blocked()]).transcribe(b"png", "p", {})
    assert r.recitation and r.text == "" and r.finish_reason == "content_filter"
    for first in (prose, blocked()):
        o = runner(tmp_path, FakeAnthropic([first, half, half])).run_page(PDF, 1, force=True)
        assert o.status == "ok" and "half-page crops" in o.text


def test_assemble_cleans_joins_and_marks(tmp_path):
    """!
    @brief The assembler drops running headers and page numbers, joins a hyphenated word and a cut sentence, keeps markers.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import assemble
    ocr = tmp_path / "ocr" / "anthropic"
    ocr.mkdir(parents=True)
    pages = {1: "<!-- page 1 -->\nJ. HEAT TRANSFER 2003\n# Title\n\nThe spreading resist-\n\n1",
             2: "<!-- page 2 -->\nJ. HEAT TRANSFER 2004\nance is large and the heat flows\n3",
             3: "<!-- page 3 -->\nJ. HEAT TRANSFER 2005\ninto the plate.\n\n$$ R = 1 \\tag{1} $$\n4"}
    for p, t in pages.items():
        (ocr / f"X_p{p}.md").write_text(t, encoding="utf-8")
    out = assemble.assemble(tmp_path, "X", tmp_path, 4, None, {1: 10, 2: 11}, True)
    assert out == assemble.assemble(tmp_path, "X", tmp_path, 4, None, {1: 10, 2: 11}, True)  # deterministic
    assert "J. HEAT TRANSFER" not in out
    assert "resistance" in out and "resist-" not in out
    assert "<!-- page 2 | printed 11 -->" in out and "<!-- page 4 | printed ? -->" in out
    assert out.count("[missing]") == 1 and "reading_status: machine" in out
    assert "- Title" in out and "\\tag{1}" in out


def test_assemble_text_layer_fills_missing_pages(tmp_path):
    """!
    @brief A page with no OCR output takes a usable text layer (provider `text`); a short or missing layer stays `[missing]`.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import assemble
    ocr = tmp_path / "ocr" / "anthropic"
    ocr.mkdir(parents=True)
    (ocr / "X_p1.md").write_text("<!-- page 1 -->\nClaude page", encoding="utf-8")
    prose = " ".join(f"word{i}" for i in range(80))
    out = assemble.assemble(tmp_path, "X", tmp_path, 3, {1: "ignored " * 100, 2: prose, 3: "too short"}, {}, True)
    assert "Claude page" in out and "word79" in out and out.count("[missing]") == 1
    assert 'text: "2"' in out


def test_assemble_ranges():
    """!
    @brief Page lists are written as ranges.
    @return None
    """
    from tools.ocr import assemble
    assert assemble.ranges([1, 2, 3, 5, 7, 8]) == "1-3,5,7-8"


def test_papermap_parsers():
    """!
    @brief The note parsers of the map: page specs, the verified/error pages, the offsets and the citation contexts.
    @return None
    """
    from tools.ocr import papermap as pm
    assert pm.parse_page_spec("1-3,7") == {1, 2, 3, 7}
    ver = pm.parse_verified("| file | pages | why | checked |\n| :-- | :-- | :-- | :-- |\n"
                            "| Foo | 1-6 | eq | p5, p6 R (Table 1); p4 ERROR eq 17; p1 not compared |\n"
                            "| Lienhard2024 | 323-325 | conv | R: 323, 325; p433 ERROR |\n")
    assert ver["Foo"]["verified"] == {5, 6} and ver["Foo"]["error"] == {4} and ver["Foo"]["listed"] == set(range(1, 7))
    assert ver["Lienhard2024"]["verified"] == {323, 325}
    assert pm.parse_offsets("| Foo | 9 | -2 | 1 / 3: low |\n| Bar | 9 | ? |  |\n") == {"Foo": -2}
    text = "see [Muzychka2003] Table 3, eq. 25, p. 8-9 and [Muzychka2003Part1] p. 4"
    ctx = pm.citations(text, "Muzychka2003")
    assert len(ctx) == 1                      # a longer key is not a match
    loc = pm.cited_locations(ctx[0])
    assert 3 in loc["tables"] and 25 in loc["eqs"] and {8, 9} <= set(loc["pages"])
    assert pm.locate("table", 3, {1: "Table 2 x", 2: "\nTable 3 Results"}) == [2]


def test_papermap_formula_score_and_build(tmp_path):
    """!
    @brief The formula density separates equations from prose, and a map is built from a fake papers folder.
    @param tmp_path Temporary folder.
    @return None
    """
    from tools.ocr import papermap as pm
    prose = "the heat flows through the board and spreads " * 20
    maths = "T = a + b ; α = β γ = 2 ; x = y ; z = w ; q = 1 ; " * 6
    assert pm.formula_score(prose)[0] < pm.FORMULA_SCORE < pm.formula_score(maths)[0]
    papers = tmp_path / "papers"
    (papers / "pdf").mkdir(parents=True)
    (papers / "pdf" / "Foo.pdf").write_bytes(b"%PDF")
    (papers / "notes").mkdir()
    (papers / "notes" / "INDEX.md").write_text("| Foo.pdf | FooKey | A paper | x | y |\n")
    (papers / "ocr" / "anthropic").mkdir(parents=True)
    (papers / "ocr" / "anthropic" / "Foo_p2.md").write_text("page two")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "theory.md").write_text("Result of [FooKey] Table 1 on p. 2.")

    def fake(path):
        t = {1: prose, 2: maths}
        return {"pages": 2, "text": t, "words": {1: 200, 2: 200}, "garbage": {1: False, 2: False},
                "formula": {p: pm.formula_score(t[p])[0] for p in t}, "equals": {p: t[p].count("=") for p in t}}

    m = pm.build_map(papers, tmp_path, fake)
    row = m["rows"][0]
    assert row["stem"] == "Foo" and row["pages"] == 2 and row["claude_pages"] == 1
    assert 2 in row["essential_pages"] and row["e1_run"] == [] and row["e1_verify_only"] == [2]
    assert "Foo" in pm.render_markdown(m)


# ---------------------------------------------------------------------------- OpenRouter (mocked transport)
from tools.ocr.providers.openrouter import OpenRouterProvider, rank_models  # noqa: E402
from tools.ocr import compare as ocr_compare  # noqa: E402

OR_KEY = "sk-or-" + "v1-" + "ab12" * 10          # built here so the source has no key-like text
OR_OK = {"model": "qwen/qwen2.5-vl-72b-instruct:free", "choices": [{"message": {"content": "page $x^2$"}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 900, "completion_tokens": 120}}
OR_MODELS = {"data": [
    {"id": "meta-llama/llama-3.2-11b-vision-instruct:free", "architecture": {"input_modalities": ["text", "image"]},
     "pricing": {"prompt": "0", "completion": "0"}, "context_length": 131072},
    {"id": "qwen/qwen2.5-vl-72b-instruct:free", "architecture": {"input_modalities": ["text", "image"]},
     "pricing": {"prompt": "0", "completion": "0"}, "context_length": 32768},
    {"id": "some/text-only:free", "architecture": {"input_modalities": ["text"]}, "pricing": {"prompt": "0", "completion": "0"}},
    {"id": "paid/vision", "architecture": {"input_modalities": ["image"]}, "pricing": {"prompt": "0.1", "completion": "0.1"}}]}


class FakeOpenRouter(OpenRouterProvider):
    """!
    @brief OpenRouter provider whose HTTP calls are scripted.
    """

    def __init__(self, answers, **kw):
        """!
        @brief Create it.
        @param answers List of dict responses or exceptions for the POSTs.
        @param kw      Extra constructor arguments.
        @return None
        """
        super().__init__(key=OR_KEY, retries=2, first_pause=0.0, sleep=lambda s: None, min_interval=0.0, **kw)
        self.answers, self.urls, self.bodies, self.sleeps, self.gets = list(answers), [], [], [], []
        self._sleep = self.sleeps.append

    def _post(self, url, body, timeout):
        """!
        @brief Scripted POST.
        @param url     URL (recorded).
        @param body    Body (recorded).
        @param timeout Unused.
        @return dict The next response.
        """
        self.urls.append(url)
        self.bodies.append(json.loads(body))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    def _get(self, url, timeout):
        """!
        @brief Scripted GET of the model list.
        @param url     URL (recorded).
        @param timeout Unused.
        @return dict The model list.
        """
        self.gets.append(url)
        return OR_MODELS


def or_error(code, message, headers=None):
    """!
    @brief Build an HTTPError in the shape of OpenRouter.
    @param code    HTTP status.
    @param message Message.
    @param headers Response headers.
    @return urllib.error.HTTPError The error.
    """
    body = json.dumps({"error": {"message": message, "code": code}})
    return urllib.error.HTTPError("http://x", code, "err", headers or {}, io.BytesIO(body.encode()))


def test_openrouter_request_shape_usage_and_key_not_in_url():
    g = FakeOpenRouter([OR_OK])
    r = g.transcribe(b"png", "prompt", {"model": "qwen/qwen2.5-vl-72b-instruct:free"})
    assert r.text == "page $x^2$" and r.extra["usage"] == {"input_tokens": 900, "output_tokens": 120}
    part = g.bodies[0]["messages"][0]["content"][0]
    assert part["type"] == "image_url" and part["image_url"]["url"].startswith("data:image/png;base64,")
    assert OR_KEY not in g.urls[0] and g.gets == []


def test_openrouter_ranks_only_free_vision_models_and_auto_walks_the_chain():
    ids = rank_models(OR_MODELS["data"])
    assert ids == ["qwen/qwen2.5-vl-72b-instruct:free", "meta-llama/llama-3.2-11b-vision-instruct:free"]
    g = FakeOpenRouter([or_error(404, "No endpoints found"), OR_OK])
    r = g.transcribe(b"png", "p", {"model": "auto"})
    assert [b["model"] for b in g.bodies] == ids and len(g.gets) == 1 and r.extra["attempts"] == 2


def test_openrouter_429_waits_retry_after_and_daily_limit_stops_at_once():
    g = FakeOpenRouter([or_error(429, "slow down", {"Retry-After": "7"}), OR_OK])
    assert g.transcribe(b"png", "p", {"model": "m:free"}).text and g.sleeps == [7.0]
    h = FakeOpenRouter([or_error(429, "Rate limit exceeded: free-models-per-day")])
    with pytest.raises(ProviderError) as e:
        h.transcribe(b"png", "p", {"model": "m:free"})
    assert e.value.quota_exhausted and len(h.urls) == 1


def test_openrouter_client_side_rate_limit_spaces_requests():
    now = [100.0]
    g = FakeOpenRouter([OR_OK, OR_OK], clock=lambda: now[0])
    g.min_interval = 3.2
    g.transcribe(b"png", "p", {"model": "m:free"})
    g.transcribe(b"png", "p", {"model": "m:free"})
    assert g.sleeps == [pytest.approx(3.2)]


def test_openrouter_error_with_a_key_never_reaches_the_message():
    g = FakeOpenRouter([or_error(401, "bad key " + OR_KEY)])
    with pytest.raises(ProviderError) as e:
        g.transcribe(b"png", "p", {"model": "m:free"})
    assert OR_KEY not in str(e.value) and "sk-or-" not in str(e.value)


def test_openrouter_is_registered_and_has_a_daily_limit():
    assert REGISTRY["openrouter"].key_env == ("OPENROUTER_API_KEY",)
    assert config.models()["openrouter"]["daily_limit"] <= 50


def test_openrouter_pages_rank_below_claude_and_disagreements_are_reported(tmp_path):
    ocr = tmp_path / "ocr"
    (ocr / "anthropic").mkdir(parents=True)
    (ocr / "openrouter").mkdir()
    (ocr / "anthropic" / "Foo_p1.md").write_text("<!-- page 1 -->\nvalue 12.5 K")
    (ocr / "openrouter" / "Foo_p1.md").write_text("<!-- page 1 -->\n<!-- model: openrouter:m:free -->\nvalue 12.6 K")
    (ocr / "openrouter" / "Foo_p2.md").write_text("<!-- page 2 -->\n<!-- model: openrouter:m:free -->\nonly openrouter here")
    (ocr / "Foo_p2.md").write_text("<!-- page 2 -->\ngemini text")
    from tools.ocr import assemble as asm
    out = asm.assemble(tmp_path, "Foo", tmp_path, 2)
    assert "value 12.5 K" in out and "only openrouter here" in out and "gemini text" not in out
    assert "model:" not in out.split("---", 2)[2]
    assert "openrouter: '1'" in out.replace('"', "'") and "disagrees_with_claude" in out
    assert "gemini text" in asm.assemble(tmp_path, "Foo", tmp_path, 2, order=("gemini", "openrouter", "claude"))


def test_compare_pages_digits_equations_similarity():
    r = ocr_compare.compare_pages("a $x$ 12 b", "a $x$ 12 b")
    assert r["agree"] and r["digits_equal"]
    assert not ocr_compare.compare_pages("a 12", "a 13")["agree"]


def _ledger_worker(path: str, tag: str, n: int) -> None:
    """!
    @brief Append `n` entries to a ledger from a separate process (helper of the concurrency test).
    @param path Ledger file.
    @param tag  Provider name written in the entries.
    @param n    Number of entries.
    @return None
    """
    from tools.ocr.ledger import Ledger
    led = Ledger(pathlib.Path(path))  # opened once: its in-memory copy goes stale while the other process writes
    for i in range(n):
        led.add(provider=tag, file="X", page=i, ok=True)


def test_ledger_concurrent_appends_keep_every_entry(tmp_path):
    """!
    @brief Two processes appending to one ledger lose no entry (lock plus re-read inside the lock).
    @param tmp_path pytest temporary folder.
    @return None
    """
    import json
    import multiprocessing as mp
    path = tmp_path / "usage.json"
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=_ledger_worker, args=(str(path), tag, 40)) for tag in ("a", "b")]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join(60)
        assert pr.exitcode == 0
    rows = json.loads(path.read_text())
    assert len(rows) == 80 and sum(r["provider"] == "a" for r in rows) == 40
    assert not list(tmp_path.glob("*.tmp"))


# ---------------------------------------------------------------- whole-page mode and the reading-status sidecar
def test_whole_page_mode_makes_one_request_and_no_crops(tmp_path):
    """!
    @brief `whole_page` never crops or falls back: a refusal fails after one request, a cut page is kept with a note, the budget is passed.
    @param tmp_path pytest temporary folder.
    @return None
    """
    p = FakeProvider([Result("", "RECITATION", recitation=True)])
    o = runner(tmp_path, p, whole_page=True, max_tokens=16000).run_page(PDF, 2)
    assert o.status == "failed" and len(p.calls) == 1 and "whole-page" in o.note
    p2 = FakeProvider([Result("long table", "max_tokens", split=True)])
    o2 = runner(tmp_path / "b", p2, whole_page=True).run_page(PDF, 3)
    assert o2.status == "ok" and "cut at the token limit" in o2.note and len(p2.calls) == 1


def _status_papers(tmp_path):
    """!
    @brief A papers folder with one three-page paper, a Claude page each, and a reviewed md-final.
    @param tmp_path pytest temporary folder.
    @return Path The papers folder.
    """
    ocr = tmp_path / "ocr" / "anthropic"
    ocr.mkdir(parents=True)
    for n in (1, 2, 3):
        (ocr / f"X_p{n}.md").write_text(f"<!-- page {n} -->\nmachine text of page {n} with enough words", encoding="utf-8")
    (tmp_path / "md-final").mkdir()
    (tmp_path / "md-final" / "X.md").write_text(
        "---\nreading_status: {verified_image: \"1\", corrected_then_verified: \"2\", verified_text_layer: \"\", other_pages: machine}   # x\n---\n\n"
        "<!-- page 1 | printed ? | verified (image) -->\n\nmachine text of page 1 with enough words\n\n"
        "<!-- page 2 | printed ? | corrected and verified (image) -->\n\nREVIEWED text of page 2\n\n<!-- reviewed: fixed a fraction -->\n\n"
        "<!-- page 3 | printed ? -->\n\nmachine text of page 3 with enough words\n", encoding="utf-8")
    return tmp_path


def test_status_seed_keeps_the_reviewed_page_through_assemble(tmp_path):
    """!
    @brief `status seed` reads the hand-written status; `assemble` then keeps the corrected text and writes the status per page.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import assemble, status
    papers = _status_papers(tmp_path)
    added = status.seed(papers)
    assert added["verified"] == 1 and added["corrected"] == 1
    assert (papers / "ocr" / "corrected" / "X_p2.md").is_file()
    out = assemble.assemble(papers, "X", papers, 3, None, {}, True)
    assert "REVIEWED text of page 2" in out and "machine text of page 2" not in out and "<!-- reviewed: fixed a fraction -->" in out
    assert "<!-- page 1 | printed ? | verified (image) -->" in out and "<!-- page 2 | printed ? | corrected and verified (image) -->" in out
    assert "<!-- page 3 | printed ? -->" in out
    assert 'reading_status: {verified: "1", corrected: "2", machine: "3"}' in out
    assert out == assemble.assemble(papers, "X", papers, 3, None, {}, True)        # deterministic
    assert status.seed(papers) == {"verified": 0, "corrected": 0, "machine": 0}      # never replaces an entry


def test_verified_state_is_lost_when_the_provider_page_changes(tmp_path):
    """!
    @brief A verified page whose provider text changed since the check is reported as machine, a corrected page is not touched.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import assemble, status
    papers = _status_papers(tmp_path)
    status.seed(papers)
    (papers / "ocr" / "anthropic" / "X_p1.md").write_text("<!-- page 1 -->\nanother transcription of page 1", encoding="utf-8")
    (papers / "ocr" / "anthropic" / "X_p2.md").write_text("<!-- page 2 -->\nanother transcription of page 2", encoding="utf-8")
    out = assemble.assemble(papers, "X", papers, 3, None, {}, True)
    assert "<!-- page 1 | printed ? -->" in out and "another transcription of page 1" in out
    assert "REVIEWED text of page 2" in out and "another transcription of page 2" not in out


def test_status_set_command_and_errors(tmp_path):
    """!
    @brief `status set` records a state (a corrected page keeps the md-final chunk), refuses a bad state and a page with nothing to keep.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import status
    papers = _status_papers(tmp_path)
    status.set_status(papers, "X", {3}, "corrected", "reviewer", "fixed eq 3")
    assert "machine text of page 3" in (papers / "ocr" / "corrected" / "X_p3.md").read_text(encoding="utf-8")
    assert status.load(papers)["X"]["3"]["note"] == "fixed eq 3"
    with pytest.raises(ValueError):
        status.set_status(papers, "X", {1}, "great")
    with pytest.raises(ValueError):
        status.set_status(papers, "X", {9}, "corrected")
    from tools.ocr.cli import main
    assert main(["--papers", str(papers), "status", "set", "X", "1", "verified", "--note", "image"]) == 0
    assert status.load(papers)["X"]["1"]["state"] == "verified" and status.load(papers)["X"]["1"].get("src_sha")


# ---------------------------------------------------------------- offline checks: firstline, eqcheck, audit
LAYER = ("Thermal spreading resistance of a circular source on a finite cylinder with side cooling\n"
         "The solution is obtained by separation of variables and the eigenvalues are the roots of the Bessel function\n"
         "of the first kind. " + "The boundary condition at the end face is convective and uniform over the surface. " * 3)


def test_firstline_clean_page_planted_invented_line_and_scan(tmp_path):
    """!
    @brief The first-line check passes a faithful page, flags an invented first sentence, and calls a scan not checkable.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import checks
    clean = "<!-- page 1 -->\nThermal spreading resistance of a circular source on a finite cylinder\n\nbody"
    assert checks.check_first_line(clean, LAYER)["verdict"] == "ok"
    invented = "<!-- page 1 -->\nThe remainder of the derivation below is followed by the rest of this page\n\nThermal spreading resistance"
    r = checks.check_first_line(invented, LAYER)
    assert r["verdict"] == "FLAG" and r["overlap"] < 0.6
    scan = checks.check_first_line(clean, "")
    assert scan["verdict"] == "not checkable" and "scan" in scan["reason"]
    garbage = checks.check_first_line(clean, "\x01\x02\x03 " * 80)
    assert garbage["verdict"] == "not checkable"


def test_firstline_moved_figure_notes_and_broken_words(tmp_path):
    """!
    @brief A line found lower on the page is `moved`, a figure description and a provider note are not compared, and a
           text layer with broken words still matches.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import checks
    lower = "<!-- page 1 -->\nThe boundary condition at the end face is convective and uniform over the surface"
    assert checks.check_first_line(lower, LAYER, n_lines=1)["verdict"] == "moved"
    fig = "<!-- page 1 -->\n[Figure: a sketch of the cylinder]\n\nThermal spreading resistance of a circular source on a finite cylinder"
    assert checks.check_first_line(fig, LAYER)["verdict"] == "ok"
    only_fig = checks.check_first_line("<!-- page 1 -->\n[Figure: a sketch]\n", LAYER)
    assert only_fig["verdict"] == "not checkable"
    note = "<!-- page 1 -->\nThermal spreading resistance of a circular source *(header, right: Summary)*"
    assert checks.check_first_line(note, LAYER)["verdict"] == "ok"
    broken = ("In\norder\nto\nform\na\nprop\ner\nblended\nsolution,\neac\nh\np\nortion\nof\nthe\nsolution\nm\nust\nb\ne\nan\nasymptote.\n"
              "This\nrequires\nthat\nthe\nb\neha\nvior\nof\nthe\nlimits\nare\nexamined\nat\nthe\nfully\ndevelop\ned\nlimit")
    page = "<!-- page 1 -->\nIn order to form a proper blended solution, each portion of the solution must be an asymptote."
    r = checks.check_first_line(page, broken)             # one fragment per line: the page match is complete, the top may be short
    assert r["verdict"] in ("ok", "moved") and r["overlap_page"] >= 0.9
    assert checks.check_first_line(page, broken, n_lines=60)["verdict"] == "ok"


def test_firstline_command_writes_a_report_and_lists_the_flagged_page(tmp_path, monkeypatch):
    """!
    @brief `firstline` over a small library (page folders of Claude, whole and corrected) writes the report and flags the planted page.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    from tools.ocr import checks
    from tools.ocr.cli import main
    (tmp_path / "pdf").mkdir()
    (tmp_path / "pdf" / "Q.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "ocr" / "anthropic" / "whole").mkdir(parents=True)
    (tmp_path / "ocr" / "corrected").mkdir()
    (tmp_path / "ocr" / "anthropic" / "Q_p1.md").write_text("<!-- page 1 -->\nThermal spreading resistance of a circular source on a finite cylinder\n", encoding="utf-8")
    (tmp_path / "ocr" / "anthropic" / "Q_p2.md").write_text("<!-- page 2 -->\nAs shown in the remainder of the page below this | line `x`\n", encoding="utf-8")
    (tmp_path / "ocr" / "anthropic" / "whole" / "Q_p3.md").write_text("<!-- page 3 -->\nThermal spreading resistance of a circular source on a finite cylinder\n", encoding="utf-8")
    (tmp_path / "ocr" / "corrected" / "Q_p4.md").write_text("<!-- page 4 -->\n$$x=1$$\n", encoding="utf-8")
    monkeypatch.setattr(checks, "pdf_layers", lambda pdf: {1: LAYER, 2: LAYER, 3: LAYER, 4: LAYER})
    assert main(["--papers", str(tmp_path), "firstline"]) == 0
    rep = (tmp_path / "notes" / "FIRSTLINE_REPORT.md").read_text(encoding="utf-8")
    assert "| Q | 2 | claude |" in rep and "| claude-whole | 1 | 1 |" in rep and "| corrected | 1 | 0 | 0 | 0 | 1 |" in rep
    assert "remainder of the page below this   line  x" in rep          # pipes and backticks of untrusted text are neutralised
    assert main(["--papers", str(tmp_path), "firstline", "--stem", "Q", "--pages", "1", "--out", str(tmp_path / "o.md")]) == 0
    assert "Pages: 1." in (tmp_path / "o.md").read_text(encoding="utf-8")
    assert main(["--papers", str(tmp_path), "firstline", "--sources", "nope"]) == 1


def _text_pdf(path, pages):
    """!
    @brief Write a born-digital PDF made on the fly with pypdfium2 (Helvetica, A4, no third-party content).
    @param path  Output file.
    @param pages List of pages; each is a list of (x, y_from_top, text, font size) in points (an empty list is a page without text).
    @return None
    """
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    doc = pdfium.PdfDocument.new()
    font = raw.FPDFText_LoadStandardFont(doc, b"Helvetica")
    for items in pages:
        page = doc.new_page(595, 842)
        for x, y, text, size in items:
            obj = raw.FPDFPageObj_CreateTextObj(doc, font, size)
            raw_text = (text + "\0").encode("utf-16-le")
            arr = (ctypes.c_ushort * (len(raw_text) // 2)).from_buffer_copy(raw_text)
            raw.FPDFText_SetText(obj, ctypes.cast(arr, ctypes.POINTER(ctypes.c_ushort)))
            raw.FPDFPageObj_Transform(obj, 1, 0, 0, 1, x, 842 - y)
            raw.FPDFPage_InsertObject(page, obj)
        page.gen_content()
    doc.save(str(path))


def test_firstline_on_a_real_pdf_when_pdfium_is_available(tmp_path):
    """!
    @brief A born-digital PDF made on the fly: an invented first line is flagged; a page without text is not checkable.
    @param tmp_path pytest temporary folder.
    @return None
    """
    pytest.importorskip("pypdfium2")
    from tools.ocr import checks
    items = [(50, 72 + 14 * i, line[:95], 9) for i, line in enumerate(LAYER.splitlines())]
    (tmp_path / "pdf").mkdir()
    _text_pdf(tmp_path / "pdf" / "R.pdf", [items, []])      # the second page has no text: a scan as far as the check can tell
    (tmp_path / "ocr" / "anthropic").mkdir(parents=True)
    (tmp_path / "ocr" / "anthropic" / "R_p1.md").write_text("<!-- page 1 -->\nA sentence that is not on the page at all, invented by the model\n\nThermal spreading resistance", encoding="utf-8")
    (tmp_path / "ocr" / "anthropic" / "R_p2.md").write_text("<!-- page 2 -->\nSome text for a page that is a picture\n", encoding="utf-8")
    res = checks.run_firstline(tmp_path)
    assert {r["page"]: r["verdict"] for r in res["rows"]} == {1: "FLAG", 2: "not checkable"}


def test_eqcheck_structure_against_layer_and_other_provider():
    """!
    @brief Equation counts, `\\tag` and trailing `\\qquad (n)` numbers are compared with the layer and with the other provider.
    @return None
    """
    from tools.ocr import checks
    md = "<!-- page 1 -->\n$$a=b \\tag{1}$$\n\ntext\n\n$$c=d \\qquad (2)$$\n"
    st = checks.md_eq_stats(md)
    assert st["display"] == 2 and st["tags"] == {"1", "2"}
    layer = "text " * 60 + "\n(1)\n(2)\n(3)\n"
    assert any("without a \\tag: 3" in i for i in checks.check_equations(md, layer))
    assert not checks.check_equations(md, "text " * 60 + "\n(1)\n(2)\n")
    heavy = "x = y + z = w " * 30
    assert any("formula heavy" in i for i in checks.check_equations("<!-- page 1 -->\nplain prose only here", heavy))
    other = "$$a$$\n$$b$$\n$$c$$\n$$d$$\n$$e$$\n$$f$$\n"
    assert any("other provider" in i for i in checks.check_equations(md, "", other))
    assert not checks.check_equations(md, "", "$$a=b \\tag{1}$$\n$$c=d \\tag{2}$$")


def test_eqcheck_command_reports_a_mismatch(tmp_path, monkeypatch):
    """!
    @brief `eqcheck` writes its report and counts the page with a missing equation number.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    from tools.ocr import checks
    from tools.ocr.cli import main
    (tmp_path / "pdf").mkdir()
    (tmp_path / "pdf" / "E.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "ocr" / "anthropic").mkdir(parents=True)
    (tmp_path / "ocr" / "anthropic" / "E_p1.md").write_text("<!-- page 1 -->\n$$a=b \\tag{1}$$\n", encoding="utf-8")
    monkeypatch.setattr(checks, "pdf_layers", lambda pdf: {1: "text " * 60 + "\n(1)\n(2)\n"})
    assert main(["--papers", str(tmp_path), "eqcheck"]) == 0
    rep = (tmp_path / "notes" / "EQCHECK_REPORT.md").read_text(encoding="utf-8")
    assert "with a mismatch: 1" in rep and "without a \\tag: 2" in rep


def _audit_library(tmp_path):
    """!
    @brief A tiny consistent library: one 3-page paper with Claude pages, a verified and a corrected page, and its md-final.
    @param tmp_path pytest temporary folder.
    @return Path The papers folder.
    """
    from tools.ocr import assemble, status
    papers = tmp_path / "papers"
    (papers / "pdf").mkdir(parents=True)
    (papers / "pdf" / "X.pdf").write_bytes(b"%PDF-1.4")
    (papers / "ocr" / "anthropic").mkdir(parents=True)
    for n in (1, 2, 3):
        (papers / "ocr" / "anthropic" / f"X_p{n}.md").write_text(f"<!-- page {n} -->\n# Section {n}\n\nmachine text of page {n} with enough words to count\n", encoding="utf-8")
    (papers / "notes").mkdir()
    status.set_status(papers, "X", {2}, "verified", "reviewer", "image", {2: status.sha((papers / "ocr" / "anthropic" / "X_p2.md").read_text(encoding="utf-8"))})
    (papers / "ocr" / "corrected").mkdir()
    (papers / "ocr" / "corrected" / "X_p3.md").write_text("<!-- page 3 -->\nCORRECTED text of page 3\n", encoding="utf-8")
    status.set_status(papers, "X", {3}, "corrected", "reviewer", "fixed")
    (papers / "md-final").mkdir()
    (papers / "md-final" / "X.md").write_text(assemble.assemble(papers, "X", tmp_path, 3, None, {}, True), encoding="utf-8")
    return papers


def _levels(res):
    """!
    @brief The findings of an audit as (level, text) pairs.
    @param res Result of `checks.audit`.
    @return list[tuple[str, str]] Level and finding text.
    """
    return [(lv, text) for lv, _, text in res["findings"]]


def test_audit_clean_library_and_every_planted_defect(tmp_path):
    """!
    @brief A consistent library has no error; each planted defect (marker gap, missing header field, missing page, stale
           status, wrong corrected text, key-like text, confidential file, page beyond the PDF, orphan) is reported.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import checks
    papers = _audit_library(tmp_path)
    clean = checks.audit(papers)
    assert [f for f in clean["findings"] if f[0] == "error"] == [], clean["findings"]
    assert clean["stats"]["marker_pages"] == {"total": 3, "machine": 1, "verified": 1, "corrected": 1}
    final = papers / "md-final" / "X.md"
    good = final.read_text(encoding="utf-8")

    final.write_text(good.replace("<!-- page 2 |", "<!-- page 9 |"), encoding="utf-8")
    assert any("not 1..3" in t for _, t in _levels(checks.audit(papers)))
    final.write_text(good.replace("pdf_pages: 3\n", ""), encoding="utf-8")
    assert any("'pdf_pages' missing" in t for _, t in _levels(checks.audit(papers)))
    final.write_text(good.replace("# Section 1\n\nmachine text of page 1 with enough words to count", "[missing]"), encoding="utf-8")
    assert any(lv == "error" and "'[missing]' but a page exists" in t for lv, t in _levels(checks.audit(papers)))
    final.write_text(good.replace("| verified (image)", ""), encoding="utf-8")
    assert any(lv == "warn" and "marker says machine" in t for lv, t in _levels(checks.audit(papers)))
    final.write_text(good.replace("CORRECTED text of page 3", "something else"), encoding="utf-8")
    assert any(lv == "error" and "corrected page not used" in t for lv, t in _levels(checks.audit(papers)))
    final.write_text(good, encoding="utf-8")
    assert not [f for f in checks.audit(papers)["findings"] if f[0] == "error"]

    key = "sk-ant-" + "a1" * 15                                   # built at run time: no key-like text in this file
    (papers / "ocr" / "anthropic" / "X_p1.md").write_text(f"<!-- page 1 -->\nleaked {key}\n", encoding="utf-8")
    res = checks.audit(papers)
    assert any(lv == "error" and "key-like text" in t for lv, t in _levels(res))
    assert key not in checks.render_audit(res)                    # never shown
    (papers / "ocr" / "anthropic" / "X_p1.md").write_text("<!-- page 1 -->\n# Section 1\n\nmachine text of page 1 with enough words to count\n", encoding="utf-8")
    (papers / "ocr" / "OdbppSpec81U4_p1.md").write_text("<!-- page 1 -->\nsecret\n", encoding="utf-8")
    (papers / "ocr" / "anthropic" / "X_p7.md").write_text("<!-- page 7 -->\nbeyond the end\n", encoding="utf-8")
    (papers / "ocr" / "Z_p1.md").write_text("<!-- page 1 -->\norphan\n", encoding="utf-8")
    lv = _levels(checks.audit(papers))
    assert any(level == "error" and "confidential file" in t for level, t in lv)
    assert any(level == "error" and "beyond the 3 PDF pages" in t for level, t in lv)
    assert any(level == "warn" and "without a PDF" in t for level, t in lv)


def test_audit_command_exit_code_and_report(tmp_path):
    """!
    @brief `audit` returns 0 and writes the report for a clean library, 1 when an error is found.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr.cli import main
    papers = _audit_library(tmp_path)
    assert main(["--papers", str(papers), "audit"]) == 0
    assert "Findings: 0 error" in (papers / "notes" / "AUDIT_REPORT.md").read_text(encoding="utf-8")
    (papers / "ocr" / "corrected" / "X_p3.md").unlink()
    assert main(["--papers", str(papers), "audit"]) == 1


def test_assemble_and_map_are_reproducible(tmp_path):
    """!
    @brief Two `assemble` runs give byte-identical files, and so do two `map` runs (offline, no provider).
    @param tmp_path pytest temporary folder.
    @return None
    """
    pytest.importorskip("pypdfium2")
    from tools.ocr.cli import main
    papers = _audit_library(tmp_path)
    _text_pdf(papers / "pdf" / "X.pdf", [[(50, 72, "page text " * 20, 9)] for _ in range(3)])
    outs = []
    for _ in range(2):
        assert main(["--papers", str(papers), "assemble", "X", "--root", str(tmp_path)]) == 0
        outs.append((papers / "md-final" / "X.md").read_bytes())
    assert outs[0] == outs[1]
    maps = []
    for _ in range(2):
        assert main(["--papers", str(papers), "map", "--root", str(tmp_path)]) == 0
        maps.append(((papers / "notes" / "OCR_MAP.md").read_bytes(), (papers / "notes" / "ocr_map.json").read_bytes()))
    assert maps[0] == maps[1]


def test_status_set_verified_refuses_a_page_that_does_not_exist(tmp_path):
    """!
    @brief `status set STEM 99 verified` for a page with no provider text, no corrected text and no md-final chunk is refused.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import status
    from tools.ocr.cli import main
    papers = _status_papers(tmp_path)
    with pytest.raises(ValueError):
        status.set_status(papers, "X", {99}, "verified")
    assert main(["--papers", str(papers), "status", "set", "X", "99", "verified"]) == 1
    assert "99" not in status.load(papers).get("X", {})
    status.set_status(papers, "X", {99}, "machine")                    # a machine entry is harmless


# ---------------------------------------------------------------- prompt variants
def test_prompt_variants_are_named_and_reach_the_runner(tmp_path):
    """!
    @brief `--prompt-variant` selects one of three alternative phrasings; the default is data/prompt.txt; an unknown name is refused.
    @param tmp_path pytest temporary folder.
    @return None
    """
    from tools.ocr import config
    from tools.ocr.cli import build_parser, make_runner
    assert config.variant_prompt(None) == config.default_prompt() == config.variant_prompt("default")
    names = set(config.prompt_variants()) - {"default"}
    assert names == {"plain", "latex", "topdown"}
    texts = {config.variant_prompt(n) for n in names}
    assert len(texts) == 3 and config.default_prompt() not in texts
    with pytest.raises(ValueError):
        config.variant_prompt("nope")
    a = build_parser().parse_args(["transcribe", "X", "--provider", "local", "--prompt-variant", "latex"])
    assert make_runner(a, tmp_path).prompt == config.variant_prompt("latex")
